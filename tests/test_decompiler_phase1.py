"""Comprehensive test suite for Mindustry Logic (mlog) Decompiler - Phase 1.

Covers:
1. Mlog lexical tokenization and instruction parsing
2. Jump target resolution and jump classification (conditional, unconditional, forward, backward, self)
3. Basic block splitting rules (entry, jump targets, post-jump, post-terminal)
4. Control Flow Graph (CFG) edge reconstruction and back-edge detection
5. Malformed mlog error rejection
6. Real-world golden mlog file CFG validation
"""

import os
import unittest

from src.decompiler.cfg import (
    BasicBlock,
    CFGBuilder,
    CFGEdge,
    ControlFlowGraph,
    EdgeType,
    build_cfg,
)
from src.decompiler.errors import DecompileError, MlogParseError
from src.decompiler.instruction import JumpType, MlogInstruction
from src.decompiler.parser import MlogParser, parse_mlog


class TestDecompilerPhase1(unittest.TestCase):
    """Unit and integration tests for Decompiler Phase 1."""

    # -----------------------------------------------------------------------
    # 1. Instruction Parsing Tests
    # -----------------------------------------------------------------------

    def test_parse_standard_opcodes(self):
        """Verify parsing standard mlog opcodes and their arguments."""
        mlog_text = (
            "set x 10\n"
            "op add y x 5\n"
            "sensor hp core1 @health\n"
            "control enabled reactor1 1 0 0 0\n"
            "ucontrol move 100 200 0 0 0\n"
            "draw clear 0 0 0 0 0 0\n"
            "drawflush display1\n"
            "read val cell1 0\n"
            "write val cell1 1\n"
            "wait 0.5\n"
            "stop\n"
        )
        instrs = parse_mlog(mlog_text)
        self.assertEqual(len(instrs), 11)

        self.assertEqual(instrs[0].address, 0)
        self.assertEqual(instrs[0].opcode, "set")
        self.assertEqual(instrs[0].args, ("x", "10"))

        self.assertEqual(instrs[1].address, 1)
        self.assertEqual(instrs[1].opcode, "op")
        self.assertEqual(instrs[1].args, ("add", "y", "x", "5"))

        self.assertEqual(instrs[2].opcode, "sensor")
        self.assertEqual(instrs[2].args, ("hp", "core1", "@health"))

        self.assertEqual(instrs[10].address, 10)
        self.assertEqual(instrs[10].opcode, "stop")
        self.assertEqual(instrs[10].args, ())
        self.assertTrue(instrs[10].is_terminal)

    def test_parse_string_literals_with_spaces_and_escapes(self):
        """Verify parsing string literals with embedded spaces, quotes, and newlines."""
        mlog_text = (
            'print "Hello World!"\n'
            'print "Line 1\\nLine 2"\n'
            'print "Quote: \\"Mindustry\\""\n'
            'printflush message1\n'
        )
        instrs = parse_mlog(mlog_text)
        self.assertEqual(len(instrs), 4)
        self.assertEqual(instrs[0].args[0], '"Hello World!"')
        self.assertEqual(instrs[1].args[0], '"Line 1\\nLine 2"')
        self.assertEqual(instrs[2].args[0], '"Quote: \\"Mindustry\\""')

    def test_comments_and_empty_lines_ignored(self):
        """Verify comments and blank lines do not increment address counter."""
        mlog_text = (
            "# Top level comment\n"
            "\n"
            "set a 1\n"
            "   # Indented comment\n"
            "\n"
            "set b 2\n"
        )
        instrs = parse_mlog(mlog_text)
        self.assertEqual(len(instrs), 2)
        self.assertEqual(instrs[0].address, 0)
        self.assertEqual(instrs[0].loc.line, 3)
        self.assertEqual(instrs[1].address, 1)
        self.assertEqual(instrs[1].loc.line, 6)

    # -----------------------------------------------------------------------
    # 2. Jump Target Resolution and Classification
    # -----------------------------------------------------------------------

    def test_conditional_vs_unconditional_jump(self):
        """Verify classification of conditional vs unconditional jumps."""
        mlog_text = (
            "jump 3 always 0 0\n"
            "jump 3 equal x 10\n"
            "jump 3 equal 0 0\n"
            "stop\n"
        )
        instrs = parse_mlog(mlog_text)

        # always is unconditional
        self.assertTrue(instrs[0].is_unconditional_jump)
        self.assertFalse(instrs[0].is_conditional_jump)
        self.assertEqual(instrs[0].jump_type, JumpType.UNCONDITIONAL)

        # equal x 10 is conditional
        self.assertFalse(instrs[1].is_unconditional_jump)
        self.assertTrue(instrs[1].is_conditional_jump)
        self.assertEqual(instrs[1].jump_type, JumpType.CONDITIONAL)

        # equal 0 0 (identical operands) is unconditional
        self.assertTrue(instrs[2].is_unconditional_jump)
        self.assertFalse(instrs[2].is_conditional_jump)

    def test_forward_backward_and_self_jumps(self):
        """Verify identification of forward, backward, and self jumps."""
        mlog_text = (
            "set i 0\n"           # 0
            "jump 3 always 0 0\n" # 1: forward jump to 3
            "set i 1\n"           # 2
            "jump 1 always 0 0\n" # 3: backward jump to 1
            "jump 4 always 0 0\n" # 4: self jump to 4
        )
        instrs = parse_mlog(mlog_text)

        self.assertTrue(instrs[1].is_forward_jump)
        self.assertFalse(instrs[1].is_backward_jump)
        self.assertEqual(instrs[1].jump_target, 3)

        self.assertFalse(instrs[3].is_forward_jump)
        self.assertTrue(instrs[3].is_backward_jump)
        self.assertEqual(instrs[3].jump_target, 1)

        self.assertTrue(instrs[4].is_self_jump)
        self.assertTrue(instrs[4].is_backward_jump)
        self.assertFalse(instrs[4].is_forward_jump)

    def test_jump_targeting_eof(self):
        """Verify jump targeting length of program (EOF yield address) is valid."""
        mlog_text = (
            "jump 2 always 0 0\n"  # 0
            "set x 1\n"            # 1
            # 2 is EOF
        )
        instrs = parse_mlog(mlog_text)
        self.assertEqual(len(instrs), 2)
        self.assertEqual(instrs[0].jump_target, 2)

    # -----------------------------------------------------------------------
    # 3. Basic Block Splitting Rules
    # -----------------------------------------------------------------------

    def test_single_linear_block_no_jumps(self):
        """A program with no jumps or terminal instructions forms exactly 1 basic block."""
        mlog_text = (
            "set x 1\n"
            "set y 2\n"
            "op add z x y\n"
        )
        cfg = build_cfg(mlog_text)
        self.assertEqual(len(cfg.blocks), 1)
        b = cfg.blocks[0]
        self.assertEqual(b.start_address, 0)
        self.assertEqual(b.end_address, 2)
        self.assertEqual(len(b.instructions), 3)
        self.assertTrue(b.is_entry)
        self.assertFalse(b.is_terminal)

    def test_basic_block_splitting_at_leaders(self):
        """Verify block splitting at: entry, jump target, post-jump, post-terminal."""
        mlog_text = (
            "sensor hp core1 @health\n"      # 0 [block 0]
            "jump 4 greaterThanEq hp 1000\n" # 1 [block 0 end: jump]
            "set alert 1\n"                  # 2 [block 1 start: post-jump]
            "jump 5 always 0 0\n"            # 3 [block 1 end: jump]
            "set alert 0\n"                  # 4 [block 2 start: jump target of 1]
            "print alert\n"                  # 5 [block 3 start: jump target of 3, post-jump of 4]
            "stop\n"                         # 6 [block 3 end: terminal]
            "set unreachable 99\n"           # 7 [block 4 start: post-terminal]
        )
        cfg = build_cfg(mlog_text)

        # Expected blocks:
        # block_0: [0..1]
        # block_1: [2..3]
        # block_2: [4..4]
        # block_3: [5..6]
        # block_4: [7..7]
        self.assertEqual(len(cfg.blocks), 5)

        self.assertEqual((cfg.blocks[0].start_address, cfg.blocks[0].end_address), (0, 1))
        self.assertEqual((cfg.blocks[1].start_address, cfg.blocks[1].end_address), (2, 3))
        self.assertEqual((cfg.blocks[2].start_address, cfg.blocks[2].end_address), (4, 4))
        self.assertEqual((cfg.blocks[3].start_address, cfg.blocks[3].end_address), (5, 6))
        self.assertEqual((cfg.blocks[4].start_address, cfg.blocks[4].end_address), (7, 7))

        self.assertTrue(cfg.blocks[3].is_terminal)
        self.assertTrue(cfg.blocks[0].is_entry)

    # -----------------------------------------------------------------------
    # 4. Control Flow Graph Edges & Flow Analysis
    # -----------------------------------------------------------------------

    def test_if_else_diamond_cfg_edges(self):
        """Verify conditional jump branching produces true-jump and fallthrough edges."""
        mlog_text = (
            "sensor hp core1 @health\n"      # 0: block_0
            "jump 4 greaterThanEq hp 1000\n" # 1: block_0 -> block_2 (true), block_1 (false)
            "set alert 1\n"                  # 2: block_1
            "jump 5 always 0 0\n"            # 3: block_1 -> block_3 (uncond)
            "set alert 0\n"                  # 4: block_2 -> block_3 (fallthrough)
            "print alert\n"                  # 5: block_3
        )
        cfg = build_cfg(mlog_text)
        self.assertEqual(len(cfg.blocks), 4)

        b0, b1, b2, b3 = cfg.blocks

        # block 0 exits to block 2 (jump true) and block 1 (fallthrough)
        self.assertEqual(len(b0.outgoing_edges), 2)
        self.assertIn(b2, b0.successors)
        self.assertIn(b1, b0.successors)

        # block 1 exits to block 3 (unconditional jump)
        self.assertEqual(len(b1.outgoing_edges), 1)
        self.assertEqual(b1.outgoing_edges[0].edge_type, EdgeType.UNCOND_JUMP)
        self.assertEqual(b1.successors, [b3])

        # block 2 falls through to block 3
        self.assertEqual(len(b2.outgoing_edges), 1)
        self.assertEqual(b2.outgoing_edges[0].edge_type, EdgeType.FALLTHROUGH)
        self.assertEqual(b2.successors, [b3])

        # block 3 has 2 predecessors: block 1 and block 2
        self.assertEqual(set(b3.predecessors), {b1, b2})

    def test_while_loop_cfg_back_edges(self):
        """Verify loop structure correctly identifies back-edges."""
        mlog_text = (
            "set i 0\n"                     # 0: block_0
            "jump 5 greaterThanEq i 10\n"   # 1: block_1 (loop header)
            "op add i i 1\n"                # 2: block_2 (loop body)
            "print i\n"                     # 3: block_2
            "jump 1 always 0 0\n"           # 4: block_2 -> back to block_1
            "stop\n"                        # 5: block_3 (loop exit)
        )
        cfg = build_cfg(mlog_text)
        self.assertEqual(len(cfg.blocks), 4)

        back_edges = cfg.get_back_edges()
        self.assertEqual(len(back_edges), 1)
        be = back_edges[0]
        self.assertTrue(be.is_back_edge)
        self.assertEqual(be.source.name, "block_2")
        self.assertEqual(be.target.name, "block_1")
        self.assertEqual(be.edge_type, EdgeType.UNCOND_JUMP)

    def test_dead_code_unreachable_block_detection(self):
        """Verify detecting unreachable code blocks after unconditional jump or stop."""
        mlog_text = (
            "set x 1\n"
            "jump 3 always 0 0\n" # 1: jump past 2
            "set x 999\n"         # 2: unreachable!
            "print x\n"           # 3
        )
        cfg = build_cfg(mlog_text)
        unreachable = cfg.get_unreachable_blocks()
        self.assertEqual(len(unreachable), 1)
        self.assertEqual(unreachable[0].start_address, 2)
        self.assertEqual(unreachable[0].instructions[0].opcode, "set")

    def test_graphviz_dot_generation(self):
        """Verify Graphviz DOT string generation."""
        mlog_text = "set x 1\nstop\n"
        cfg = build_cfg(mlog_text)
        dot = cfg.to_dot()
        self.assertIn("digraph CFG", dot)
        self.assertIn("block_0", dot)

    # -----------------------------------------------------------------------
    # 5. Malformed Mlog Rejection Tests
    # -----------------------------------------------------------------------

    def test_reject_unknown_opcode(self):
        """Verify unknown opcodes are rejected with MlogParseError."""
        with self.assertRaises(MlogParseError) as ctx:
            parse_mlog("invalid_opcode 1 2 3\n")
        self.assertIn("Unknown mlog opcode: 'invalid_opcode'", str(ctx.exception))

    def test_reject_invalid_arg_counts(self):
        """Verify opcodes with too few or too many arguments are rejected."""
        bad_cases = [
            ("set x\n", "expects 2 argument(s)"),
            ("sensor a b\n", "expects 3 argument(s)"),
            ("op add a\n", "expects 4 argument(s)"),
            ("stop 123\n", "expects 0 argument(s)"),
        ]
        for code, expected_msg in bad_cases:
            with self.subTest(code=code):
                with self.assertRaises(MlogParseError) as ctx:
                    parse_mlog(code)
                self.assertIn(expected_msg, str(ctx.exception))

    def test_reject_unterminated_string(self):
        """Verify unterminated string literals raise MlogParseError."""
        with self.assertRaises(MlogParseError) as ctx:
            parse_mlog('print "unclosed string\n')
        self.assertIn("Unterminated string literal", str(ctx.exception))

    def test_reject_non_numeric_and_negative_jump_target(self):
        """Verify non-numeric or negative jump targets are rejected."""
        with self.assertRaises(MlogParseError) as ctx:
            parse_mlog("jump target_label always 0 0\n")
        self.assertIn("must be a numeric address", str(ctx.exception))

        with self.assertRaises(MlogParseError) as ctx:
            parse_mlog("jump -5 always 0 0\n")
        self.assertIn("cannot be negative", str(ctx.exception))

    def test_reject_out_of_bounds_jump_target(self):
        """Verify jumps targeting past the end of the program are rejected."""
        with self.assertRaises(MlogParseError) as ctx:
            parse_mlog("set x 1\njump 100 always 0 0\n")
        self.assertIn("out-of-bounds address 100", str(ctx.exception))

    def test_reject_invalid_condition_op(self):
        """Verify invalid jump conditions are rejected."""
        with self.assertRaises(MlogParseError) as ctx:
            parse_mlog("jump 0 badCondition a b\n")
        self.assertIn("Invalid jump condition: 'badCondition'", str(ctx.exception))

    def test_reject_token_overflow(self):
        """Verify lines with more than 16 tokens are rejected."""
        line = "ucontrol " + " ".join(["0"] * 16) + "\n"
        with self.assertRaises(MlogParseError) as ctx:
            parse_mlog(line)
        self.assertIn("exceeds maximum 16 tokens", str(ctx.exception))

    def test_reject_instruction_limit_overflow(self):
        """Verify programs with > 1000 instructions are rejected."""
        big_program = "\n".join(["set x 1"] * 1001)
        with self.assertRaises(MlogParseError) as ctx:
            parse_mlog(big_program)
        self.assertIn("exceeds maximum 1000 instructions", str(ctx.exception))

    def test_reject_jump_limit_overflow(self):
        """Verify programs with > 500 jumps are rejected."""
        big_jumps = "\n".join(["jump 0 always 0 0"] * 501)
        with self.assertRaises(MlogParseError) as ctx:
            parse_mlog(big_jumps)
        self.assertIn("exceeds maximum 500 jumps", str(ctx.exception))

    # -----------------------------------------------------------------------
    # 6. Real-World Golden Mlog File CFG Validation
    # -----------------------------------------------------------------------

    def test_golden_examples_cfg_reconstruction(self):
        """Verify CFG reconstruction on verified compiler output files."""
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        examples_dirs = [
            os.path.join(root_dir, "examples"),
            os.path.join(root_dir, "..", "mlog-compiler-skill", "examples"),
        ]

        golden_files = []
        for edir in examples_dirs:
            if os.path.exists(edir):
                for root, _, fnames in os.walk(edir):
                    for fname in fnames:
                        if fname.endswith(".mlog"):
                            golden_files.append(os.path.join(root, fname))

        self.assertGreater(len(golden_files), 0, "Must find golden .mlog files")

        for fpath in golden_files:
            with self.subTest(file=os.path.basename(fpath)):
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()

                cfg = build_cfg(content, filename=fpath)
                self.assertGreater(len(cfg.instructions), 0)
                self.assertGreater(len(cfg.blocks), 0)
                self.assertIsNotNone(cfg.entry_block)
                self.assertEqual(cfg.entry_block.start_address, 0)

                # Verify all instructions belong to exactly one block
                all_covered = set()
                for b in cfg.blocks:
                    for instr in b.instructions:
                        self.assertNotIn(instr.address, all_covered)
                        all_covered.add(instr.address)
                self.assertEqual(len(all_covered), len(cfg.instructions))

                # Verify predecessor-successor graph symmetry
                for b in cfg.blocks:
                    for succ in b.successors:
                        self.assertIn(b, succ.predecessors)
                    for pred in b.predecessors:
                        self.assertIn(b, pred.successors)


if __name__ == "__main__":
    unittest.main()
