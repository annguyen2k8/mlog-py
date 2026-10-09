package mindustry.test;

import arc.Core;
import arc.mock.MockFiles;
import arc.struct.Seq;
import mindustry.Vars;
import mindustry.core.ContentLoader;
import mindustry.logic.GlobalVars;
import mindustry.logic.LAssembler;
import mindustry.logic.LStatement;
import mindustry.logic.LStatements;

import mindustry.logic.LExecutor;
import mindustry.logic.LVar;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;

public class MindustryHarness {
    public static void main(String[] args) {
        boolean runMode = false;
        int maxSteps = 10000;
        for (int i = 0; i < args.length; i++) {
            if ("--run".equals(args[i])) {
                runMode = true;
                if (i + 1 < args.length && !args[i + 1].startsWith("--")) {
                    try {
                        maxSteps = Integer.parseInt(args[++i]);
                    } catch (NumberFormatException ignored) {}
                }
            } else if ("--steps".equals(args[i]) && i + 1 < args.length) {
                try {
                    maxSteps = Integer.parseInt(args[++i]);
                } catch (NumberFormatException ignored) {}
            }
        }

        try {
            Core.files = new MockFiles();
            Vars.content = new ContentLoader();
            Vars.content.createBaseContent();
            Vars.logicVars = new GlobalVars();
            Vars.logicVars.init();

            StringBuilder sb = new StringBuilder();
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    sb.append(line).append("\n");
                }
            }

            String mlog = sb.toString();
            Seq<LStatement> stmts = LAssembler.read(mlog, false);

            for (int i = 0; i < stmts.size; i++) {
                LStatement s = stmts.get(i);
                if (s instanceof LStatements.InvalidStatement) {
                    System.err.println("Line " + (i + 1) + ": Mindustry rejected statement as InvalidStatement");
                    System.exit(1);
                }
            }

            LAssembler asm = LAssembler.assemble(mlog, false);
            if (asm.instructions == null) {
                System.err.println("Assembly produced null instruction array");
                System.exit(1);
            }

            for (int i = 0; i < asm.instructions.length; i++) {
                if (asm.instructions[i] == null) {
                    System.err.println("Instruction " + i + " assembled to null");
                    System.exit(1);
                }
            }

            if (runMode) {
                LExecutor exec = new LExecutor();
                exec.load(asm);
                int steps = 0;
                while (exec.counter.numval < exec.instructions.length && exec.counter.numval >= 0 && !exec.stop && steps < maxSteps) {
                    exec.runOnce();
                    steps++;
                }

                System.out.println("RUN_OK:" + steps);
                for (LVar v : exec.vars) {
                    if (v != null && v.name != null && !v.name.startsWith("@") && !v.name.startsWith("___")) {
                        if (v.isobj) {
                            System.out.println("VAR:" + v.name + "=" + (v.objval != null ? v.objval.toString() : "null"));
                        } else {
                            System.out.println("VAR:" + v.name + "=" + v.numval);
                        }
                    }
                }
            } else {
                System.out.println("OK:" + asm.instructions.length);
            }
            System.exit(0);
        } catch (Throwable t) {
            System.err.println("ERROR: " + t.getMessage());
            t.printStackTrace(System.err);
            System.exit(2);
        }
    }
}
