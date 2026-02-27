delete window.$;
let wpRequire = webpackChunkdiscord_app.push([[Symbol()], {}, (r) => r]);
webpackChunkdiscord_app.pop();

// ===========================================================================
//  Safe module lookup — crashes with a clear message instead of cryptic TypeError
// ===========================================================================
function findModule(predicate, name) {
  const mod = Object.values(wpRequire.c).find(predicate);
  if (!mod) {
    throw new Error(
      `[Quest Completer] Could not find ${name} module. Discord may have updated — this script needs updating.`,
    );
  }
  return mod;
}

const ApplicationStreamingStore = findModule(
  (x) => x?.exports?.A?.__proto__?.getStreamerActiveStreamMetadata,
  "ApplicationStreamingStore",
).exports.A;
const RunningGameStore = findModule(
  (x) => x?.exports?.Ay?.getRunningGames,
  "RunningGameStore",
).exports.Ay;
const QuestsStore = findModule(
  (x) => x?.exports?.A?.__proto__?.getQuest,
  "QuestsStore",
).exports.A;
const ChannelStore = findModule(
  (x) => x?.exports?.A?.__proto__?.getAllThreadsForParent,
  "ChannelStore",
).exports.A;
const GuildChannelStore = findModule(
  (x) => x?.exports?.Ay?.getSFWDefaultChannel,
  "GuildChannelStore",
).exports.Ay;
const FluxDispatcher = findModule(
  (x) => x?.exports?.h?.__proto__?.flushWaitQueue,
  "FluxDispatcher",
).exports.h;
const api = findModule((x) => x?.exports?.Bo?.get, "API").exports.Bo;

// ===========================================================================
//  Retry wrapper — retries API calls on failure with exponential backoff
// ===========================================================================
async function apiWithRetry(method, options, maxRetries = 3) {
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await api[method](options);
    } catch (err) {
      if (attempt === maxRetries) {
        console.error(
          `[Quest Completer] API ${method.toUpperCase()} ${options.url} failed after ${maxRetries + 1} attempts:`,
          err,
        );
        throw err;
      }
      const backoff = Math.min(1000 * 2 ** attempt, 10000);
      console.warn(
        `[Quest Completer] API ${method.toUpperCase()} ${options.url} failed (attempt ${attempt + 1}/${maxRetries + 1}), retrying in ${backoff}ms...`,
      );
      await new Promise((resolve) => setTimeout(resolve, backoff));
    }
  }
}

// ===========================================================================
//  Quest discovery
// ===========================================================================
const supportedTasks = [
  "WATCH_VIDEO",
  "PLAY_ON_DESKTOP",
  "STREAM_ON_DESKTOP",
  "PLAY_ACTIVITY",
  "WATCH_VIDEO_ON_MOBILE",
];

const quests = [...QuestsStore.quests.values()].filter(
  (x) =>
    x.userStatus?.enrolledAt &&
    !x.userStatus?.completedAt &&
    new Date(x.config.expiresAt).getTime() > Date.now() &&
    supportedTasks.find((y) =>
      Object.keys(
        (x.config.taskConfig ?? x.config.taskConfigV2).tasks,
      ).includes(y),
    ),
);

const isApp = typeof DiscordNative !== "undefined";

if (quests.length === 0) {
  console.log("[Quest Completer] No uncompleted quests found!");
} else {
  console.log(
    `[Quest Completer] Found ${quests.length} uncompleted quest(s).`,
  );

  // Process quests sequentially with a simple async loop instead of recursion
  (async function processQuests() {
    while (quests.length > 0) {
      const quest = quests.pop();
      if (!quest) break;

      const pid = Math.floor(Math.random() * 30000) + 1000;

      const applicationId = quest.config.application.id;
      const applicationName = quest.config.application.name;
      const questName = quest.config.messages.questName;
      const taskConfig = quest.config.taskConfig ?? quest.config.taskConfigV2;
      const taskName = supportedTasks.find((x) => taskConfig.tasks[x] != null);
      const secondsNeeded = taskConfig.tasks[taskName].target;
      let secondsDone = quest.userStatus?.progress?.[taskName]?.value ?? 0;

      try {
        // ===================================================================
        //  WATCH_VIDEO / WATCH_VIDEO_ON_MOBILE
        //  Sends accelerated video-progress POSTs.
        //  maxFuture = 10: server rejects timestamps >10s ahead of wall clock
        //  speed = 7: seconds of progress claimed per POST (~7x real time)
        //  interval = 1: seconds between loop iterations
        // ===================================================================
        if (
          taskName === "WATCH_VIDEO" ||
          taskName === "WATCH_VIDEO_ON_MOBILE"
        ) {
          const maxFuture = 10;
          const speed = 7;
          const interval = 1;
          const enrolledAt = new Date(quest.userStatus.enrolledAt).getTime();
          let completed = false;

          console.log(
            `[Quest Completer] Spoofing video for "${questName}". ETA: ~${Math.ceil((secondsNeeded - secondsDone) / speed)} seconds.`,
          );

          while (!completed && secondsDone < secondsNeeded) {
            const maxAllowed =
              Math.floor((Date.now() - enrolledAt) / 1000) + maxFuture;
            const diff = maxAllowed - secondsDone;
            const timestamp = secondsDone + speed;

            if (diff >= speed) {
              const res = await apiWithRetry("post", {
                url: `/quests/${quest.id}/video-progress`,
                body: {
                  timestamp: Math.min(
                    secondsNeeded,
                    timestamp + Math.random(),
                  ),
                },
              });
              completed = res.body.completed_at != null;
              secondsDone = Math.min(secondsNeeded, timestamp);
            }

            if (secondsDone >= secondsNeeded) break;
            await new Promise((r) => setTimeout(r, interval * 1000));
          }

          if (!completed) {
            await apiWithRetry("post", {
              url: `/quests/${quest.id}/video-progress`,
              body: { timestamp: secondsNeeded },
            });
          }

          console.log(`[Quest Completer] "${questName}" completed!`);

          // ===================================================================
          //  PLAY_ON_DESKTOP
          //  Injects a fake game process into RunningGameStore.
          //  Server sends QUESTS_SEND_HEARTBEAT_SUCCESS on its own schedule.
          //  Cleanup is guaranteed via try/finally even if interrupted.
          // ===================================================================
        } else if (taskName === "PLAY_ON_DESKTOP") {
          if (!isApp) {
            console.log(
              `[Quest Completer] PLAY_ON_DESKTOP requires the Discord desktop app. Cannot complete "${questName}" in browser.`,
            );
            continue;
          }

          const res = await apiWithRetry("get", {
            url: `/applications/public?application_ids=${applicationId}`,
          });
          const appData = res.body[0];
          const exeName =
            appData.executables
              ?.find((x) => x.os === "win32")
              ?.name?.replace(">", "") ??
            appData.name.replace(/[\/\\:*?"<>|]/g, "");

          const fakeGame = {
            cmdLine: `C:\\Program Files\\${appData.name}\\${exeName}`,
            exeName,
            exePath: `c:/program files/${appData.name.toLowerCase()}/${exeName}`,
            hidden: false,
            isLauncher: false,
            id: applicationId,
            name: appData.name,
            pid: pid,
            pidPath: [pid],
            processName: appData.name,
            start: Date.now(),
          };

          const realGames = RunningGameStore.getRunningGames();
          const fakeGames = [fakeGame];
          const realGetRunningGames = RunningGameStore.getRunningGames;
          const realGetGameForPID = RunningGameStore.getGameForPID;

          try {
            RunningGameStore.getRunningGames = () => fakeGames;
            RunningGameStore.getGameForPID = (pid) =>
              fakeGames.find((x) => x.pid === pid);
            FluxDispatcher.dispatch({
              type: "RUNNING_GAMES_CHANGE",
              removed: realGames,
              added: [fakeGame],
              games: fakeGames,
            });

            console.log(
              `[Quest Completer] Spoofed game to "${applicationName}". Waiting ~${Math.ceil((secondsNeeded - secondsDone) / 60)} minutes for "${questName}".`,
            );

            // Wait for completion via Flux event
            await new Promise((resolve) => {
              const fn = (data) => {
                const progress =
                  quest.config.configVersion === 1
                    ? data.userStatus.streamProgressSeconds
                    : Math.floor(
                        data.userStatus.progress.PLAY_ON_DESKTOP.value,
                      );
                console.log(
                  `[Quest Completer] ${questName}: ${progress}/${secondsNeeded}s`,
                );

                if (progress >= secondsNeeded) {
                  FluxDispatcher.unsubscribe(
                    "QUESTS_SEND_HEARTBEAT_SUCCESS",
                    fn,
                  );
                  resolve();
                }
              };
              FluxDispatcher.subscribe("QUESTS_SEND_HEARTBEAT_SUCCESS", fn);
            });

            console.log(`[Quest Completer] "${questName}" completed!`);
          } finally {
            // Always restore original functions, even if interrupted
            RunningGameStore.getRunningGames = realGetRunningGames;
            RunningGameStore.getGameForPID = realGetGameForPID;
            FluxDispatcher.dispatch({
              type: "RUNNING_GAMES_CHANGE",
              removed: [fakeGame],
              added: [],
              games: [],
            });
          }

          // ===================================================================
          //  STREAM_ON_DESKTOP
          //  Monkey-patches stream metadata to fake streaming the quest game.
          //  Cleanup is guaranteed via try/finally.
          // ===================================================================
        } else if (taskName === "STREAM_ON_DESKTOP") {
          if (!isApp) {
            console.log(
              `[Quest Completer] STREAM_ON_DESKTOP requires the Discord desktop app. Cannot complete "${questName}" in browser.`,
            );
            continue;
          }

          const realFunc =
            ApplicationStreamingStore.getStreamerActiveStreamMetadata;

          try {
            ApplicationStreamingStore.getStreamerActiveStreamMetadata = () => ({
              id: applicationId,
              pid,
              sourceName: null,
            });

            console.log(
              `[Quest Completer] Spoofed stream to "${applicationName}". Stream any window in VC for ~${Math.ceil((secondsNeeded - secondsDone) / 60)} minutes.`,
            );
            console.log(
              "[Quest Completer] You need at least 1 other person in the VC!",
            );

            // Wait for completion via Flux event
            await new Promise((resolve) => {
              const fn = (data) => {
                const progress =
                  quest.config.configVersion === 1
                    ? data.userStatus.streamProgressSeconds
                    : Math.floor(
                        data.userStatus.progress.STREAM_ON_DESKTOP.value,
                      );
                console.log(
                  `[Quest Completer] ${questName}: ${progress}/${secondsNeeded}s`,
                );

                if (progress >= secondsNeeded) {
                  FluxDispatcher.unsubscribe(
                    "QUESTS_SEND_HEARTBEAT_SUCCESS",
                    fn,
                  );
                  resolve();
                }
              };
              FluxDispatcher.subscribe("QUESTS_SEND_HEARTBEAT_SUCCESS", fn);
            });

            console.log(`[Quest Completer] "${questName}" completed!`);
          } finally {
            ApplicationStreamingStore.getStreamerActiveStreamMetadata =
              realFunc;
          }

          // ===================================================================
          //  PLAY_ACTIVITY
          //  Sends heartbeat POSTs every 20s (server-enforced minimum interval).
          //  Handles both configVersion 1 and 2.
          // ===================================================================
        } else if (taskName === "PLAY_ACTIVITY") {
          // Find a valid channel — DM first, then any guild voice channel
          const dmChannel = ChannelStore.getSortedPrivateChannels()[0];
          let channelId = dmChannel?.id;

          if (!channelId) {
            const guilds = Object.values(GuildChannelStore.getAllGuilds());
            const guildWithVocal = guilds.find(
              (x) => x != null && x.VOCAL.length > 0,
            );
            if (!guildWithVocal) {
              console.error(
                `[Quest Completer] No DM channels or guild voice channels found. Cannot complete "${questName}".`,
              );
              continue;
            }
            channelId = guildWithVocal.VOCAL[0].channel.id;
          }

          const streamKey = `call:${channelId}:1`;

          console.log(
            `[Quest Completer] Completing "${questName}" via activity heartbeats. ETA: ~${Math.ceil((secondsNeeded - secondsDone) / 60)} minutes.`,
          );

          while (true) {
            const res = await apiWithRetry("post", {
              url: `/quests/${quest.id}/heartbeat`,
              body: { stream_key: streamKey, terminal: false },
            });

            // Handle both configVersion 1 and 2
            const progress =
              quest.config.configVersion === 1
                ? res.body.progress?.PLAY_ACTIVITY?.value ??
                  res.body.userStatus?.streamProgressSeconds ??
                  0
                : Math.floor(
                    res.body.progress?.PLAY_ACTIVITY?.value ?? 0,
                  );
            console.log(
              `[Quest Completer] ${questName}: ${progress}/${secondsNeeded}s`,
            );

            // Check completion BEFORE sleeping (not after)
            if (progress >= secondsNeeded) {
              await apiWithRetry("post", {
                url: `/quests/${quest.id}/heartbeat`,
                body: { stream_key: streamKey, terminal: true },
              });
              break;
            }

            // 20s interval — server-enforced minimum between heartbeats
            await new Promise((r) => setTimeout(r, 20 * 1000));
          }

          console.log(`[Quest Completer] "${questName}" completed!`);
        }
      } catch (err) {
        console.error(
          `[Quest Completer] Error completing "${questName}":`,
          err,
        );
        // Continue to next quest instead of stopping entirely
      }
    }

    console.log("[Quest Completer] All quests processed.");
  })();
}
