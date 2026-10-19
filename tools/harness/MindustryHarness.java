package mindustry.test;

import arc.Core;
import arc.Files;
import arc.files.Fi;
import arc.mock.MockFiles;
import arc.struct.Seq;
import mindustry.Vars;
import mindustry.core.ContentLoader;
import mindustry.core.GameState;
import mindustry.core.Logic;
import mindustry.core.World;
import mindustry.game.SpawnGroup;
import mindustry.logic.GlobalVars;
import mindustry.logic.LAssembler;
import mindustry.logic.LStatement;
import mindustry.logic.LStatements;

import mindustry.logic.LExecutor;
import mindustry.logic.LVar;

import mindustry.content.Blocks;
import mindustry.content.UnitTypes;
import mindustry.game.Team;
import mindustry.gen.Building;
import mindustry.gen.Groups;
import mindustry.gen.Unit;
import mindustry.world.Block;
import mindustry.world.Tile;
import mindustry.world.blocks.logic.LogicBlock;
import mindustry.world.blocks.logic.LogicDisplay;
import mindustry.world.blocks.logic.MemoryBlock;
import mindustry.world.blocks.logic.MessageBlock;
import mindustry.world.blocks.storage.CoreBlock;
import mindustry.ai.BlockIndexer;
import mindustry.ai.WaveSpawner;
import mindustry.world.meta.BlockFlag;
import arc.util.Time;
import arc.graphics.g2d.Font;
import arc.graphics.g2d.TextureRegion;
import mindustry.ui.Fonts;
import mindustry.net.Net;

import java.io.BufferedReader;
import java.io.File;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;

public class MindustryHarness {
    public static void clearTeamData(mindustry.game.Teams.TeamData data) {
        if (data == null) return;
        data.units.clear();
        if (data.unitTree != null) data.unitTree.clear();
        if (data.unitsByType != null) {
            for (int i = 0; i < data.unitsByType.length; i++) {
                if (data.unitsByType[i] != null) data.unitsByType[i].clear();
            }
        }
        data.buildings.clear();
        data.cores.clear();
        if (data.buildingTree != null) data.buildingTree.clear();
        if (data.turretTree != null) data.turretTree.clear();
        data.buildingTypes.clear();
        data.unitCap = 0;
        data.unitCount = 0;
        data.lastCore = null;
    }

    public static void resetWorld() {
        Groups.clear();
        Groups.init();

        for (Team t : Team.all) {
            clearTeamData(t.data());
        }
        Vars.state.teams.present.clear();
        Vars.state.teams.present.add(Team.sharded.data());

        for (int x = 0; x < 100; x++) {
            for (int y = 0; y < 100; y++) {
                Vars.world.tiles.set(x, y, new Tile(x, y));
            }
        }

        Vars.indexer = new BlockIndexer();
        Vars.spawner = new WaveSpawner();
        arc.Events.fire(new mindustry.game.EventType.WorldLoadEvent());

        Vars.state.set(GameState.State.playing);
        Vars.state.rules = new mindustry.game.Rules();
        Vars.state.rules.allowLogicData = true;
        SpawnGroup defaultGroup = new SpawnGroup(UnitTypes.flare);
        defaultGroup.begin = 0;
        defaultGroup.end = 100;
        defaultGroup.unitAmount = 1;
        Vars.state.rules.spawns.clear();
        Vars.state.rules.spawns.add(defaultGroup);
        Vars.state.rules.mission = null;
        Vars.state.markers.clear();
        Vars.state.tick = 0;
        Vars.state.wave = 1;
        Vars.state.wavetime = 0f;

        Time.time = 10000f;
        Time.delta = 1.0f;

        Vars.logicVars = new GlobalVars();
        Vars.logicVars.init();

        if (Vars.ui instanceof SafeUI sui) {
            sui.hasAnnounce = false;
            sui.lastAnnounceText = null;
            sui.lastAnnounceDuration = 0;
            sui.lastToastText = null;
            sui.lastToastDuration = 0;
            if (sui.hudfrag instanceof SafeHudFragment shf) {
                shf.hasToast = false;
                shf.lastToastText = null;
            }
        }
        if (Vars.control != null && Vars.control.input != null) {
            Vars.control.input.logicCutscene = false;
            Vars.control.input.logicHideHud = false;
            Vars.control.input.logicCutsceneZoom = 0;
            Vars.control.input.logicCamSpeed = 0;
            if (Vars.control.input.logicCamPan != null) {
                Vars.control.input.logicCamPan.set(0, 0);
            }
        }
        if (Vars.renderer != null) {
            try {
                java.lang.reflect.Field sf = mindustry.core.Renderer.class.getDeclaredField("shakeIntensity");
                sf.setAccessible(true);
                sf.setFloat(Vars.renderer, 0f);
            } catch (Throwable ignored) {}
        }
    }

    public static void initEnvironment() {
        Core.files = new MockFiles() {
            @Override
            public Fi get(String path, Files.FileType type) {
                if ("logicids.dat".equals(path)) {
                    File f1 = new File("../Mindustry/core/assets/logicids.dat");
                    if (f1.exists()) return new Fi(f1);
                    File f2 = new File("logicids.dat");
                    if (f2.exists()) return new Fi(f2);
                }
                return super.get(path, type);
            }
        };
        Vars.state = new GameState();
        Vars.state.set(GameState.State.playing);
        Vars.state.rules.allowLogicData = true;
        arc.Core.app = new arc.mock.MockApplication();
        arc.Core.camera = new arc.graphics.Camera();
        arc.Core.audio = new arc.mock.MockAudio();
        Core.settings = new arc.Settings();
        Core.settings.put("locale", "default");
        arc.Core.assets = new arc.assets.AssetManager();
        Vars.content = new ContentLoader();
        Vars.content.createBaseContent();
        Vars.content.units().each(u -> {
            for (mindustry.type.Weapon w : u.weapons) {
                if (w.bullet != null) {
                    w.bullet.afterPatch();
                }
            }
            u.init();
        });
        Vars.content.blocks().each(mindustry.world.Block::init);
        Vars.logicVars = new GlobalVars();
        Vars.logicVars.init();
        Groups.init();
        Vars.world = new World();
        Vars.world.resize(100, 100);
        for (int x = 0; x < 100; x++) {
            for (int y = 0; y < 100; y++) {
                Vars.world.tiles.set(x, y, new Tile(x, y));
            }
        }
        Vars.world.setGenerating(true);
        Vars.headless = false;
        try {
            java.lang.reflect.Field uf = sun.misc.Unsafe.class.getDeclaredField("theUnsafe");
            uf.setAccessible(true);
            sun.misc.Unsafe unsafe = (sun.misc.Unsafe)uf.get(null);
            Vars.renderer = (mindustry.core.Renderer)unsafe.allocateInstance(mindustry.core.Renderer.class);
            Vars.renderer.enableEffects = false;

            mindustry.input.DesktopInput dInput = (mindustry.input.DesktopInput)unsafe.allocateInstance(mindustry.input.DesktopInput.class);
            dInput.logicCamPan = new arc.math.geom.Vec2();
            Vars.control = (mindustry.core.Control)unsafe.allocateInstance(mindustry.core.Control.class);
            Vars.control.input = dInput;
            Vars.control.sound = (mindustry.audio.SoundControl)unsafe.allocateInstance(mindustry.audio.SoundControl.class);

            SafeUI safeUi = (SafeUI)unsafe.allocateInstance(SafeUI.class);
            SafeHudFragment safeHud = (SafeHudFragment)unsafe.allocateInstance(SafeHudFragment.class);
            safeUi.hudfrag = safeHud;
            Vars.ui = safeUi;
        } catch (Throwable ignored) {}
        Vars.mods = new mindustry.mod.Mods();
        Vars.net = new Net(null);
        Vars.indexer = new BlockIndexer();
        Vars.spawner = new WaveSpawner();
        Vars.logic = new Logic();
        if (Vars.state.rules.spawns.isEmpty()) {
            SpawnGroup defaultGroup = new SpawnGroup(UnitTypes.flare);
            defaultGroup.begin = 0;
            defaultGroup.end = 100;
            defaultGroup.unitAmount = 1;
            Vars.state.rules.spawns.add(defaultGroup);
        }
        arc.Events.fire(new mindustry.game.EventType.WorldLoadEvent());
        if (Fonts.logic == null) {
            Font.FontData fData = new Font.FontData();
            fData.spaceXadvance = 5f;
            fData.lineHeight = 7f;
            for (char c = 32; c < 127; c++) {
                Font.Glyph g = new Font.Glyph();
                g.id = c;
                g.xadvance = 5;
                fData.setGlyph(c, g);
            }
            Seq<TextureRegion> fRegs = new Seq<>();
            fRegs.add(new TextureRegion());
            Fonts.logic = new Font(fData, fRegs, true) {
                @Override
                protected void load(Font.FontData d) {
                    // no-op: avoid requiring OpenGL texture initialization in headless harness
                }
            };
        }
    }

    public static void main(String[] args) {
        boolean daemonMode = false;
        boolean runMode = false;
        int maxSteps = 10000;
        String procType = "logic";
        for (int i = 0; i < args.length; i++) {
            if ("--daemon".equals(args[i])) {
                daemonMode = true;
            } else if ("--run".equals(args[i])) {
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
            } else if ("--processor".equals(args[i]) && i + 1 < args.length) {
                procType = args[++i].toLowerCase();
            }
        }

        try {
            initEnvironment();
        } catch (Throwable t) {
            System.err.println("Init error: " + t.getMessage());
            t.printStackTrace(System.err);
            System.exit(2);
        }

        if (daemonMode) {
            System.out.println("READY");
            System.out.flush();
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    line = line.trim();
                    if (line.isEmpty()) continue;
                    if ("EXIT".equals(line) || "QUIT".equals(line)) {
                        break;
                    }
                    if ("PING".equals(line)) {
                        System.out.println("PONG");
                        System.out.println("<<<END_RESULT>>>");
                        System.out.flush();
                        continue;
                    }
                    try {
                        if (line.startsWith("VALIDATE ")) {
                            String[] parts = line.split(" ", 3);
                            String pType = parts.length > 1 ? parts[1] : "logic";
                            String b64 = parts.length > 2 ? parts[2] : "";
                            String mlog = new String(java.util.Base64.getDecoder().decode(b64), StandardCharsets.UTF_8);
                            processRequest(mlog, false, 0, pType, System.out, true);
                        } else if (line.startsWith("RUN ")) {
                            String[] parts = line.split(" ", 4);
                            int steps = parts.length > 1 ? Integer.parseInt(parts[1]) : 1000;
                            String pType = parts.length > 2 ? parts[2] : "logic";
                            String b64 = parts.length > 3 ? parts[3] : "";
                            String mlog = new String(java.util.Base64.getDecoder().decode(b64), StandardCharsets.UTF_8);
                            processRequest(mlog, true, steps, pType, System.out, true);
                        } else {
                            System.out.println("ERR:Unknown command: " + line);
                        }
                    } catch (Throwable t) {
                        System.out.println("ERR:" + (t.getMessage() != null ? t.getMessage() : t.toString()));
                    } finally {
                        System.out.println("<<<END_RESULT>>>");
                        System.out.flush();
                    }
                }
            } catch (Throwable t) {
                System.err.println("Daemon error: " + t.getMessage());
            }
            System.exit(0);
        } else {
            StringBuilder sb = new StringBuilder();
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    sb.append(line).append("\n");
                }
            } catch (Exception e) {
                System.err.println("Read error: " + e.getMessage());
                System.exit(1);
            }

            try {
                boolean ok = processRequest(sb.toString(), runMode, maxSteps, procType, System.out, false);
                System.exit(ok ? 0 : 1);
            } catch (Throwable t) {
                System.err.println("ERROR: " + t.getMessage());
                t.printStackTrace(System.err);
                System.exit(2);
            }
        }
    }

    public static boolean processRequest(String mlog, boolean runMode, int maxSteps, String procType, java.io.PrintStream out, boolean isDaemon) throws Exception {
        if ("logic".equals(procType)) {
            if (mlog.contains("#processor: hyper") || mlog.contains("#processor:hyper")) {
                procType = "hyper";
            } else if (mlog.contains("#processor: world") || mlog.contains("#processor:world")) {
                procType = "world";
            } else if (mlog.contains("#processor: micro") || mlog.contains("#processor:micro")) {
                procType = "micro";
            }
        }
        boolean isPrivileged = "world".equals(procType);

        if (runMode) {
            resetWorld();
        }

        Seq<LStatement> stmts = LAssembler.read(mlog, isPrivileged);
        Seq<String[]> rawStatements = extractStatementTokens(mlog);

        for (int i = 0; i < stmts.size; i++) {
            LStatement s = stmts.get(i);
            if (s instanceof LStatements.InvalidStatement) {
                String[] toks = i < rawStatements.size ? rawStatements.get(i) : null;
                if (toks != null && toks.length == 1 && "noop".equals(toks[0])) {
                    continue;
                }
                String repr = toks != null ? String.join(" ", toks) : "";
                String msg = "Line " + (i + 1) + ": Mindustry rejected statement as InvalidStatement" + (repr.isEmpty() ? "" : ": '" + repr + "'");
                if (isDaemon) {
                    out.println("ERR:" + msg);
                } else {
                    System.err.println(msg);
                }
                return false;
            }
        }

        LAssembler asm = LAssembler.assemble(mlog, isPrivileged);
        if (asm.instructions == null) {
            String msg = "Assembly produced null instruction array";
            if (isDaemon) {
                out.println("ERR:" + msg);
            } else {
                System.err.println(msg);
            }
            return false;
        }

        for (int i = 0; i < asm.instructions.length; i++) {
            if (asm.instructions[i] == null) {
                String msg = "Instruction " + i + " assembled to null";
                if (isDaemon) {
                    out.println("ERR:" + msg);
                } else {
                    System.err.println(msg);
                }
                return false;
            }
        }

        if (runMode) {
            LogicBlock procBlock = (LogicBlock)Blocks.logicProcessor;
                if ("hyper".equals(procType)) {
                    procBlock = (LogicBlock)Blocks.hyperProcessor;
                } else if ("micro".equals(procType)) {
                    procBlock = (LogicBlock)Blocks.microProcessor;
                } else if ("world".equals(procType)) {
                    procBlock = (LogicBlock)Blocks.worldProcessor;
                }

                LogicBlock.LogicBuild procBuild = (LogicBlock.LogicBuild)procBlock.newBuilding();
                Tile procTile = new Tile(50, 50);
                Vars.world.tiles.set(50, 50, procTile);
                procBuild.tile = procTile;
                procTile.build = procBuild;
                try {
                    java.lang.reflect.Field bf = Tile.class.getDeclaredField("block");
                    bf.setAccessible(true);
                    bf.set(procTile, procBlock);
                } catch (Exception ignored) {}
                procBuild.set(50 * 8f, 50 * 8f);
                procBuild.team = Team.sharded;
                procBuild.block = procBlock;
                procBuild.health = procBuild.maxHealth;
                procBuild.ipt = procBlock.instructionsPerTick;
                if (Team.sharded.data().buildingTree == null) {
                    Team.sharded.data().buildingTree = new arc.math.geom.QuadTree<>(Vars.world.getQuadBounds(new arc.math.geom.Rect()));
                }
                Team.sharded.data().buildingTree.clear();
                Team.sharded.data().buildingTree.insert(procBuild);
                Team.sharded.data().buildings.add(procBuild);
                Team.sharded.data().buildingTypes.get(procBlock, () -> new Seq<>(false)).add(procBuild);

                MessageBlock mb = (MessageBlock)Vars.content.block("message");
                if (mb == null && Blocks.message != null) {
                    mb = (MessageBlock)Blocks.message;
                }

                MemoryBlock memCellBlock = (MemoryBlock)Vars.content.block("memory-cell");
                if (memCellBlock == null && Blocks.memoryCell != null) {
                    memCellBlock = (MemoryBlock)Blocks.memoryCell;
                }

                MemoryBlock memBankBlock = (MemoryBlock)Vars.content.block("memory-bank");
                if (memBankBlock == null && Blocks.memoryBank != null) {
                    memBankBlock = (MemoryBlock)Blocks.memoryBank;
                }

                Block duoBlock = Vars.content.block("duo");
                if (duoBlock == null && Blocks.duo != null) {
                    duoBlock = Blocks.duo;
                }

                LogicDisplay dispBlock = (LogicDisplay)Vars.content.block("logic-display");
                if (dispBlock == null && Blocks.logicDisplay != null) {
                    dispBlock = (LogicDisplay)Blocks.logicDisplay;
                }

                Block switchBlock = Vars.content.block("switch");
                if (switchBlock == null && Blocks.switchBlock != null) {
                    switchBlock = Blocks.switchBlock;
                }

                Block containerBlock = Blocks.container != null ? Blocks.container : Vars.content.block("container");
                Block payConvBlock = Blocks.payloadConveyor != null ? Blocks.payloadConveyor : Vars.content.block("payload-conveyor");

                Seq<Building> linkedBuilds = new Seq<>();
                Seq<String> linkNames = new Seq<>();
                for (String lineStr : mlog.split("\n")) {
                    lineStr = lineStr.trim();
                    if (lineStr.matches("(?i)^#\\s*(links?|linked)\\s*:.*$")) {
                        String payload = lineStr.substring(lineStr.indexOf(':') + 1).trim();
                        for (String item : payload.split("[,\\s]+")) {
                            item = item.trim();
                            if (!item.isEmpty() && !linkNames.contains(item)) {
                                linkNames.add(item);
                            }
                        }
                    }
                }
                for (LVar v : asm.vars.values()) {
                    if (v != null && v.name != null && !linkNames.contains(v.name)) {
                        linkNames.add(v.name);
                    }
                }

                Building containerLinked = null;
                for (String vname : linkNames) {
                    LVar v = asm.getVar(vname);
                    boolean isMsg = vname.matches("^(enemy_|dead_)?(message|enemymessage)[0-9]*$");
                    boolean isCell = vname.matches("^(enemy_|dead_)?cell[0-9]*$");
                    boolean isBank = vname.matches("^(enemy_|dead_)?bank[0-9]*$");
                    boolean isTurret = vname.matches("^(enemy_|dead_)?(duo|turret)[0-9]*$");
                    boolean isDisplay = vname.matches("^(enemy_|dead_)?(display|logicDisplay|largelogicdisplay)[0-9]*$");
                    boolean isSwitch = vname.matches("^(enemy_|dead_)?switch[0-9]*$");
                    boolean isContainer = vname.matches("^(enemy_|dead_)?(container|storage)[0-9]*$");
                    boolean isPayloadConveyor = vname.matches("^(enemy_|dead_)?(conv|conveyor|payloadconveyor)[0-9]*$");

                    int offset = linkedBuilds.size + 1;
                    Tile t = new Tile(50 + offset, 50);
                    Vars.world.tiles.set(50 + offset, 50, t);

                    Building b = null;
                    if (mb != null && isMsg) {
                        MessageBlock.MessageBuild mbld = (MessageBlock.MessageBuild)mb.newBuilding();
                        b = mbld;
                        b.block = mb;
                    } else if (memCellBlock != null && isCell) {
                        MemoryBlock.MemoryBuild cbld = (MemoryBlock.MemoryBuild)memCellBlock.newBuilding();
                        b = cbld;
                        b.block = memCellBlock;
                    } else if (memBankBlock != null && isBank) {
                        MemoryBlock.MemoryBuild bbld = (MemoryBlock.MemoryBuild)memBankBlock.newBuilding();
                        b = bbld;
                        b.block = memBankBlock;
                    } else if (duoBlock != null && isTurret) {
                        b = duoBlock.newBuilding();
                        b.block = duoBlock;
                    } else if (dispBlock != null && isDisplay) {
                        LogicDisplay.LogicDisplayBuild dbld = (LogicDisplay.LogicDisplayBuild)dispBlock.newBuilding();
                        b = dbld;
                        b.block = dispBlock;
                    } else if (switchBlock != null && isSwitch) {
                        b = switchBlock.newBuilding();
                        b.block = switchBlock;
                    } else if (containerBlock != null && isContainer) {
                        b = containerBlock.newBuilding();
                        b.block = containerBlock;
                        if (b.items == null) {
                            b.items = new mindustry.world.modules.ItemModule();
                        }
                        b.items.set(mindustry.content.Items.copper, 100);
                    } else if (payConvBlock != null && isPayloadConveyor) {
                        b = payConvBlock.newBuilding();
                        b.block = payConvBlock;
                    }

                    if (b != null) {
                        b.tile = t;
                        t.build = b;
                        try {
                            java.lang.reflect.Field bf = Tile.class.getDeclaredField("block");
                            bf.setAccessible(true);
                            bf.set(t, b.block);
                        } catch (Exception ignored) {}
                        b.set(procBuild.x + offset * 8f, procBuild.y);
                        b.team = (vname.contains("enemy") ? Team.crux : Team.sharded);
                        if (vname.contains("dead")) {
                            b.dead = true;
                        }
                        b.health = b.maxHealth;
                        int rad = b.block != null ? (b.block.size - 1) / 2 : 0;
                        for (int dx = -rad; dx <= rad; dx++) {
                            for (int dy = -rad; dy <= rad; dy++) {
                                int tx = t.x + dx, ty = t.y + dy;
                                if (tx >= 0 && tx < 100 && ty >= 0 && ty < 100) {
                                    Tile subT = Vars.world.tile(tx, ty);
                                    if (subT != null) subT.build = b;
                                }
                            }
                        }
                        if (v != null) {
                            v.setlink(b);
                        }
                        linkedBuilds.add(b);
                        if (b.team != null) {
                            if (b.team.data().buildingTree == null) {
                                b.team.data().buildingTree = new arc.math.geom.QuadTree<>(Vars.world.getQuadBounds(new arc.math.geom.Rect()));
                            }
                            b.team.data().buildingTree.insert(b);
                            b.team.data().buildings.add(b);
                            b.team.data().buildingTypes.get(b.block, () -> new Seq<>(false)).add(b);
                        }
                        if (isContainer) {
                            containerLinked = b;
                        }
                    }
                }

                Block coreBlock = Vars.content.block("core-shard");
                if (coreBlock == null && Blocks.coreShard != null) {
                    coreBlock = Blocks.coreShard;
                }
                if (coreBlock != null) {
                    Tile coreTile = new Tile(40, 40);
                    Vars.world.tiles.set(40, 40, coreTile);
                    CoreBlock.CoreBuild coreBuild = (CoreBlock.CoreBuild)coreBlock.newBuilding();
                    coreBuild.tile = coreTile;
                    coreTile.build = coreBuild;
                    coreBuild.set(40 * 8f, 40 * 8f);
                    coreBuild.team = Team.sharded;
                    coreBuild.block = coreBlock;
                    coreBuild.health = coreBuild.maxHealth;
                    if (mlog.contains("damaged_core")) {
                        coreBuild.health = coreBuild.maxHealth * 0.5f;
                        Vars.indexer.notifyHealthChanged(coreBuild);
                    }
                    Team.sharded.data().cores.add(coreBuild);
                    Team.sharded.data().buildings.add(coreBuild);
                    Team.sharded.data().buildingTypes.get(coreBlock, () -> new Seq<>(false)).add(coreBuild);
                    Vars.indexer.getFlagged(Team.sharded, BlockFlag.core).add(coreBuild);
                    Team.sharded.data().buildingTree.insert(coreBuild);
                }

                Tile spawnTile = new Tile(10, 10);
                Vars.world.tiles.set(10, 10, spawnTile);
                Vars.spawner.getSpawns().add(spawnTile);

                Tile oreTile = new Tile(25, 25);
                Vars.world.tiles.set(25, 25, oreTile);
                if (Blocks.stone != null) {
                    oreTile.setFloor(Blocks.stone.asFloor());
                }
                if (Blocks.oreCopper != null) {
                    oreTile.setOverlay(Blocks.oreCopper);
                }
                Vars.indexer.addIndex(oreTile);

                Team.sharded.data().unitCap = 100;
                Team.crux.data().unitCap = 100;

                Unit shardedFlare1 = UnitTypes.flare.create(Team.sharded);
                shardedFlare1.set(procBuild.x + 10f, procBuild.y + 10f);
                shardedFlare1.health = shardedFlare1.maxHealth;
                shardedFlare1.spawnedByCore = true;
                shardedFlare1.add();
                Team.sharded.data().tree().insert(shardedFlare1);
                Team.sharded.data().units.add(shardedFlare1);
                if (mlog.contains("unit_with_items")) {
                    shardedFlare1.stack.set(mindustry.content.Items.copper, 15);
                }
                if (containerLinked != null) {
                    shardedFlare1.set(containerLinked.x + 2f, containerLinked.y + 2f);
                }



                Unit shardedFlare2 = UnitTypes.flare.create(Team.sharded);
                shardedFlare2.set(procBuild.x + 20f, procBuild.y + 20f);
                shardedFlare2.health = shardedFlare2.maxHealth;
                shardedFlare2.spawnedByCore = true;
                shardedFlare2.add();
                Team.sharded.data().tree().insert(shardedFlare2);
                Team.sharded.data().units.add(shardedFlare2);

                if (!Vars.state.teams.present.contains(Team.sharded.data())) {
                    Vars.state.teams.present.add(Team.sharded.data());
                }

                if (Team.sharded.data().unitsByType == null || Team.sharded.data().unitsByType.length <= UnitTypes.flare.id) {
                    Team.sharded.data().unitsByType = new Seq[Vars.content.units().size];
                }
                if (Team.sharded.data().unitsByType[UnitTypes.flare.id] == null) {
                    Team.sharded.data().unitsByType[UnitTypes.flare.id] = new Seq<>();
                }
                Team.sharded.data().unitsByType[UnitTypes.flare.id].clear();
                Team.sharded.data().unitsByType[UnitTypes.flare.id].add(shardedFlare1);
                Team.sharded.data().unitsByType[UnitTypes.flare.id].add(shardedFlare2);

                if (mlog.contains("payload_units") || mlog.contains("mega_unit") || mlog.contains("payload_conveyor")) {
                    Unit megaUnit = UnitTypes.mega.create(Team.sharded);
                    megaUnit.set(procBuild.x + 10f, procBuild.y + 10f);
                    megaUnit.health = megaUnit.maxHealth;
                    megaUnit.spawnedByCore = false;
                    megaUnit.add();
                    Team.sharded.data().tree().insert(megaUnit);
                    Team.sharded.data().units.add(megaUnit);

                    Unit daggerUnit = UnitTypes.dagger.create(Team.sharded);
                    daggerUnit.set(megaUnit.x, megaUnit.y);
                    daggerUnit.health = daggerUnit.maxHealth;
                    daggerUnit.spawnedByCore = false;
                    daggerUnit.add();
                    Team.sharded.data().tree().insert(daggerUnit);
                    Team.sharded.data().units.add(daggerUnit);

                    if (Team.sharded.data().unitsByType.length > UnitTypes.mega.id) {
                        if (Team.sharded.data().unitsByType[UnitTypes.mega.id] == null) {
                            Team.sharded.data().unitsByType[UnitTypes.mega.id] = new Seq<>();
                        }
                        Team.sharded.data().unitsByType[UnitTypes.mega.id].clear();
                        Team.sharded.data().unitsByType[UnitTypes.mega.id].add(megaUnit);
                    }
                    if (Team.sharded.data().unitsByType.length > UnitTypes.dagger.id) {
                        if (Team.sharded.data().unitsByType[UnitTypes.dagger.id] == null) {
                            Team.sharded.data().unitsByType[UnitTypes.dagger.id] = new Seq<>();
                        }
                        Team.sharded.data().unitsByType[UnitTypes.dagger.id].clear();
                        Team.sharded.data().unitsByType[UnitTypes.dagger.id].add(daggerUnit);
                    }

                    for (LVar v : asm.vars.values()) {
                        if (v != null && v.name != null && (v.name.equals("bound_mega") || v.name.equals("mega1"))) {
                            v.setobj(megaUnit);
                        }
                        if (v != null && v.name != null && (v.name.equals("ground_dagger") || v.name.equals("dagger1"))) {
                            v.setobj(daggerUnit);
                        }
                    }
                }

                if (mlog.contains("payload_conveyor") || mlog.contains("pay_enter") || mlog.contains("dagger_before_dead")) {
                    Building targetConv = null;
                    for (Building lb : linkedBuilds) {
                        if (lb.block instanceof mindustry.world.blocks.payloads.PayloadBlock) {
                            targetConv = lb;
                            break;
                        }
                    }
                    float cx = targetConv != null && targetConv.tile != null ? targetConv.tile.worldx() : procBuild.x + 10f;
                    float cy = targetConv != null && targetConv.tile != null ? targetConv.tile.worldy() : procBuild.y + 10f;

                    Unit payDagger = UnitTypes.dagger.create(Team.sharded);
                    payDagger.set(cx, cy);
                    payDagger.health = payDagger.maxHealth;
                    payDagger.spawnedByCore = false;
                    payDagger.add();
                    Team.sharded.data().tree().insert(payDagger);
                    Team.sharded.data().units.add(payDagger);

                    if (Team.sharded.data().unitsByType.length > UnitTypes.dagger.id) {
                        if (Team.sharded.data().unitsByType[UnitTypes.dagger.id] == null) {
                            Team.sharded.data().unitsByType[UnitTypes.dagger.id] = new Seq<>();
                        }
                        Team.sharded.data().unitsByType[UnitTypes.dagger.id].clear();
                        Team.sharded.data().unitsByType[UnitTypes.dagger.id].add(payDagger);
                    }

                    for (LVar v : asm.vars.values()) {
                        if (v != null && v.name != null && (v.name.equals("pay_dagger") || v.name.equals("enter_unit"))) {
                            v.setobj(payDagger);
                        }
                    }
                }

                for (LVar v : asm.vars.values()) {
                    if (v != null && v.name != null && (v.name.equals("friendly_unit") || v.name.equals("my_unit") || v.name.equals("bound_unit"))) {
                        v.setobj(shardedFlare1);
                    }
                }

                boolean hasFarOnly = mlog.contains("far_enemy_unit") && !mlog.contains("near_enemy_unit");
                if (!hasFarOnly && (mlog.contains("near_enemy_unit") || (mlog.contains("enemy_unit") && !mlog.contains("far_enemy_unit")) || mlog.contains("enemyunit") || mlog.contains("mock_unit") || mlog.contains("uradar"))) {
                    Unit unit = UnitTypes.flare.create(Team.crux);
                    unit.set(procBuild.x + 15f, procBuild.y + 15f);
                    unit.health = mlog.contains("damaged_enemy") ? unit.maxHealth * 0.5f : unit.maxHealth;
                    unit.spawnedByCore = true;
                    unit.add();
                    Team.crux.data().tree().insert(unit);
                    Team.crux.data().units.add(unit);
                    if (!Vars.state.teams.present.contains(Team.crux.data())) {
                        Vars.state.teams.present.add(Team.crux.data());
                    }
                    for (LVar v : asm.vars.values()) {
                        if (v != null && v.name != null && (v.name.equals("enemy_unit") || v.name.equals("enemyunit") || v.name.equals("mock_unit") || v.name.equals("near_enemy_unit"))) {
                            v.setobj(unit);
                        }
                    }
                }
                if (mlog.contains("mid_enemy_unit")) {
                    Unit midUnit = UnitTypes.flare.create(Team.crux);
                    midUnit.set(procBuild.x + 30f, procBuild.y + 30f);
                    midUnit.health = midUnit.maxHealth;
                    midUnit.spawnedByCore = true;
                    midUnit.add();
                    Team.crux.data().tree().insert(midUnit);
                    Team.crux.data().units.add(midUnit);
                    if (!Vars.state.teams.present.contains(Team.crux.data())) {
                        Vars.state.teams.present.add(Team.crux.data());
                    }
                    for (LVar v : asm.vars.values()) {
                        if (v != null && v.name != null && v.name.equals("mid_enemy_unit")) {
                            v.setobj(midUnit);
                        }
                    }
                }
                if (mlog.contains("far_enemy_unit")) {
                    Unit farUnit = UnitTypes.flare.create(Team.crux);
                    farUnit.set(procBuild.x + 500f, procBuild.y + 500f);
                    farUnit.health = farUnit.maxHealth;
                    farUnit.spawnedByCore = true;
                    farUnit.add();
                    Team.crux.data().tree().insert(farUnit);
                    Team.crux.data().units.add(farUnit);
                    if (!Vars.state.teams.present.contains(Team.crux.data())) {
                        Vars.state.teams.present.add(Team.crux.data());
                    }
                    for (LVar v : asm.vars.values()) {
                        if (v != null && v.name != null && v.name.equals("far_enemy_unit")) {
                            v.setobj(farUnit);
                        }
                    }
                }

                if (asm.getVar("@this") != null) asm.getVar("@this").setconst(procBuild);
                if (asm.getVar("@thisx") != null) asm.getVar("@thisx").setnum(procBuild.tileX());
                if (asm.getVar("@thisy") != null) asm.getVar("@thisy").setnum(procBuild.tileY());
                if (asm.getVar("@ipt") != null) asm.getVar("@ipt").setnum(procBuild.ipt);
                if (asm.getVar("@links") != null) asm.getVar("@links").setnum(linkedBuilds.size);

                if (Vars.ui instanceof SafeUI sui) {
                    sui.hasAnnounce = mlog.contains("#announce_busy");
                    if (sui.hudfrag instanceof SafeHudFragment shf) {
                        shf.hasToast = mlog.contains("#toast_busy");
                    }
                }

                LExecutor exec = new LExecutor();
                exec.team = Team.sharded;
                exec.build = procBuild;
                procBuild.executor = exec;
                if (procBlock.privileged) {
                    exec.privileged = true;
                }
                if (linkedBuilds.size > 0) {
                    exec.links = linkedBuilds.toArray(Building.class);
                }
                exec.load(asm);

                if (exec.thisv != null) {
                    exec.thisv.setconst(procBuild);
                }

                int steps = 0;
                int ticks = 0;
                float virtualDelta = 1.0f;
                Time.delta = virtualDelta;
                Time.time = 10000f;
                Vars.logicVars.update();

                float accumulator = procBuild.ipt;

                while (exec.counter.numval < exec.instructions.length && exec.counter.numval >= 0 && !exec.stop && steps < maxSteps && ticks < maxSteps) {
                    if (accumulator > procBlock.maxInstructionScale * procBuild.ipt) {
                        accumulator = procBlock.maxInstructionScale * procBuild.ipt;
                    }

                    while (accumulator >= 1f && exec.counter.numval < exec.instructions.length && exec.counter.numval >= 0 && !exec.stop && steps < maxSteps) {
                        exec.runOnce();
                        for (Unit u : Groups.unit) {
                            if (u != null && u.type != null && u.team != null && !u.dead) {
                                if (!u.team.data().units.contains(u)) {
                                    u.team.data().units.add(u);
                                    u.team.data().tree().insert(u);
                                    if (!Vars.state.teams.present.contains(u.team.data())) {
                                        Vars.state.teams.present.add(u.team.data());
                                    }
                                }
                            }
                        }
                        if (Vars.state != null && Vars.state.teams != null) {
                            Vars.state.teams.updateTeamStats();
                        }
                        Vars.logicVars.update();
                        steps++;
                        if (exec.yield) {
                            exec.yield = false;
                            break;
                        }
                        accumulator--;
                    }

                    ticks++;
                    Vars.state.tick++;
                    Time.delta = virtualDelta;
                    Time.time += virtualDelta;
                    Vars.logicVars.update();
                    Vars.logicVars.set("@minute", Vars.state.tick / 3600.0);

                    accumulator += virtualDelta * procBuild.ipt;
                }

                System.out.println("RUN_OK:" + steps);
                System.out.println("TICKS:" + ticks);
                System.out.println("IPT:" + procBuild.ipt);

                // Export textBuffer as Base64 to safely handle all Unicode characters, newlines, and emojis
                String textBuf = exec.textBuffer.toString();
                String tbB64 = java.util.Base64.getEncoder().encodeToString(textBuf.getBytes(StandardCharsets.UTF_8));
                System.out.println("TEXT_BUFFER_B64:" + tbB64);
                System.out.println("TEXT_BUFFER_LEN:" + textBuf.length());

                // Export flushed message contents for linked message blocks
                for (LVar v : exec.vars) {
                    if (v != null && v.isobj && v.objval instanceof MessageBlock.MessageBuild mbld) {
                        String msgB64 = java.util.Base64.getEncoder().encodeToString(mbld.message.toString().getBytes(StandardCharsets.UTF_8));
                        System.out.println("MSG_FLUSH_B64:" + v.name + "=" + msgB64);
                    }
                }

                System.out.println("GRAPHICS_BUFFER_SIZE:" + exec.graphicsBuffer.size);

                for (LVar v : exec.vars) {
                    if (v != null && v.isobj && v.objval instanceof LogicDisplay.LogicDisplayBuild dbld) {
                        System.out.println("DISPLAY_COMMANDS:" + v.name + "=" + dbld.commands.size);
                        System.out.println("DISPLAY_OPS:" + v.name + "=" + dbld.operations);
                    }
                }

                if (exec.unit != null && exec.unit.obj() instanceof Unit u) {
                    System.out.println("BOUND_UNIT:" + (u.type != null ? u.type.name : "unit"));
                } else {
                    System.out.println("BOUND_UNIT:null");
                }

                if (Vars.ui instanceof SafeUI sui) {
                    if (sui.lastAnnounceText != null) {
                        String aB64 = java.util.Base64.getEncoder().encodeToString(sui.lastAnnounceText.getBytes(StandardCharsets.UTF_8));
                        System.out.println("ANNOUNCE_B64:" + aB64);
                        System.out.println("ANNOUNCE_DUR:" + sui.lastAnnounceDuration);
                    }
                    if (sui.lastToastText != null) {
                        String tB64 = java.util.Base64.getEncoder().encodeToString(sui.lastToastText.getBytes(StandardCharsets.UTF_8));
                        System.out.println("TOAST_B64:" + tB64);
                        System.out.println("TOAST_DUR:" + sui.lastToastDuration);
                    }
                    if (sui.hudfrag instanceof SafeHudFragment shf && shf.lastToastText != null) {
                        String nB64 = java.util.Base64.getEncoder().encodeToString(shf.lastToastText.getBytes(StandardCharsets.UTF_8));
                        System.out.println("NOTIFY_B64:" + nB64);
                    }
                }

                if (Vars.state != null && Vars.state.rules != null && Vars.state.rules.mission != null) {
                    String mB64 = java.util.Base64.getEncoder().encodeToString(Vars.state.rules.mission.getBytes(StandardCharsets.UTF_8));
                    System.out.println("MISSION_B64:" + mB64);
                }

                if (Vars.control != null && Vars.control.input != null) {
                    System.out.println("CUTSCENE_ACTIVE:" + Vars.control.input.logicCutscene);
                    System.out.println("CUTSCENE_HIDE_HUD:" + Vars.control.input.logicHideHud);
                    System.out.println("CUTSCENE_ZOOM:" + Vars.control.input.logicCutsceneZoom);
                    System.out.println("CUTSCENE_SPEED:" + Vars.control.input.logicCamSpeed);
                    if (Vars.control.input.logicCamPan != null) {
                        System.out.println("CUTSCENE_PAN_X:" + Vars.control.input.logicCamPan.x);
                        System.out.println("CUTSCENE_PAN_Y:" + Vars.control.input.logicCamPan.y);
                    }
                }

                if (Vars.renderer != null) {
                    try {
                        java.lang.reflect.Field sf = mindustry.core.Renderer.class.getDeclaredField("shakeIntensity");
                        sf.setAccessible(true);
                        float si = (float)sf.get(Vars.renderer);
                        System.out.println("RENDERER_SHAKE_INTENSITY:" + si);
                    } catch (Throwable ignored) {}
                }

                if (Vars.state != null && Vars.state.markers != null) {
                    System.out.println("MARKERS_TOTAL:" + Vars.state.markers.size());
                    for (int mid = 0; mid < 20; mid++) {
                        if (Vars.state.markers.has(mid)) {
                            var m = Vars.state.markers.get(mid);
                            System.out.println("MARKER_EXISTS:" + mid + "=true");
                            if (m instanceof mindustry.game.MapObjectives.PosMarker pm) {
                                System.out.println("MARKER_POS:" + mid + "=" + pm.pos.x + "," + pm.pos.y);
                            }
                        }
                    }
                }

                for (LVar v : exec.vars) {
                    if (v != null && v.name != null && !v.name.startsWith("@") && !v.name.startsWith("___")) {
                        if (v.isobj) {
                            if (v.objval instanceof Building b) {
                                System.out.println("VAR:" + v.name + "=" + (b.block != null ? b.block.name : "building"));
                            } else if (v.objval instanceof Unit u) {
                                System.out.println("VAR:" + v.name + "=" + (u.type != null ? u.type.name : "unit"));
                            } else if (v.objval instanceof mindustry.ctype.UnlockableContent uc) {
                                System.out.println("VAR:" + v.name + "=" + uc.name);
                            } else {
                                System.out.println("VAR:" + v.name + "=" + (v.objval != null ? v.objval.toString() : "null"));
                            }
                        } else {
                            System.out.println("VAR:" + v.name + "=" + v.numval);
                        }
                    }
                }
            } else {
                System.out.println("OK:" + asm.instructions.length);
            }
            return true;
        }

    private static Seq<String[]> extractStatementTokens(String text) {
        if (text == null || text.isEmpty()) return new Seq<>();
        char[] chars = text.toCharArray();
        for (int i = 0; i < chars.length; i++) {
            if (chars[i] == '\r') chars[i] = '\n';
        }

        Seq<String[]> result = new Seq<>();
        String[] tokens = new String[32];
        int pos = 0;
        int line = 0;

        while (pos < chars.length && line < LExecutor.maxInstructions) {
            char c = chars[pos];
            if (c == '\n' || c == ';' || c == ' ') {
                pos++;
                continue;
            }

            boolean expectNext = false;
            int tok = 0;

            while (pos < chars.length) {
                char ch = chars[pos];
                if (tok >= tokens.length) break;
                if (ch == '\n' || ch == ';') break;

                if (expectNext && ch != ' ' && ch != '#' && ch != '\t') {
                    break;
                }
                expectNext = false;

                if (ch == '#') {
                    while (pos < chars.length && chars[pos++] != '\n');
                    break;
                } else if (ch == '"') {
                    int from = pos;
                    while (++pos < chars.length) {
                        char sc = chars[pos];
                        if (sc == '\\' && pos + 1 < chars.length && (chars[pos + 1] == 'n' || chars[pos + 1] == '"' || chars[pos + 1] == '\\')) {
                            pos++;
                            continue;
                        }
                        if (sc == '\\' && pos + 1 < chars.length && chars[pos + 1] == 'u') {
                            pos += 5;
                            continue;
                        }
                        if (sc == '\n' || sc == '"') break;
                    }
                    if (pos < chars.length && chars[pos] == '"') pos++;
                    if (tok < tokens.length) tokens[tok++] = new String(chars, from, pos - from);
                    expectNext = true;
                } else if (ch != ' ' && ch != '\t') {
                    int from = pos;
                    while (pos < chars.length) {
                        char tc = chars[pos];
                        if (tc == '\n' || tc == ' ' || tc == '#' || tc == '\t' || tc == ';' || tc == '"') break;
                        pos++;
                    }
                    if (tok < tokens.length) tokens[tok++] = new String(chars, from, pos - from);
                    expectNext = true;
                } else {
                    pos++;
                }
            }

            if (tok > 0) {
                if (tok == 1 && tokens[0].length() > 0 && tokens[0].charAt(tokens[0].length() - 1) == ':') {
                    // Jump label declaration - does not produce an LStatement in LParser
                } else {
                    String[] copy = new String[tok];
                    System.arraycopy(tokens, 0, copy, 0, tok);
                    result.add(copy);
                    line++;
                }
            }
        }
        return result;
    }

    public static class SafeHudFragment extends mindustry.ui.fragments.HudFragment {
        public boolean hasToast = false;
        public String lastToastText = null;

        @Override
        public boolean hasToast() {
            return hasToast;
        }

        @Override
        public void showToast(arc.scene.style.Drawable icon, String text) {
            lastToastText = text;
        }

        @Override
        public void showToast(arc.scene.style.Drawable icon, float size, String text) {
            lastToastText = text;
        }

        @Override
        public void showToast(String text) {
            lastToastText = text;
        }
    }

    public static class SafeUI extends mindustry.core.UI {
        public boolean hasAnnounce = false;
        public String lastAnnounceText = null;
        public float lastAnnounceDuration = 0;
        public String lastToastText = null;
        public float lastToastDuration = 0;

        @Override
        public boolean hasAnnouncement() {
            return hasAnnounce;
        }

        @Override
        public void announce(String text, float duration) {
            lastAnnounceText = text;
            lastAnnounceDuration = duration;
        }

        @Override
        public void showInfoToast(String text, float duration) {
            lastToastText = text;
            lastToastDuration = duration;
        }
    }
}
