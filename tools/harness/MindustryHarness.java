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

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;

public class MindustryHarness {
    public static void main(String[] args) {
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

            System.out.println("OK:" + asm.instructions.length);
            System.exit(0);
        } catch (Throwable t) {
            System.err.println("ERROR: " + t.getMessage());
            t.printStackTrace(System.err);
            System.exit(2);
        }
    }
}
