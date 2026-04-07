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

function findExport(predicate, exportPath, name) {
  const mod = findModule(predicate, name);
  const result = exportPath(mod);
  if (!result) {
    console.error(`[Quest Completer] Found ${name} module but export path returned undefined. Module exports:`, Object.keys(mod.exports || {}));
    throw new Error(`[Quest Completer] ${name} export path is broken — Discord may have changed its internal structure.`);
  }
  return result;
}

const ApplicationStreamingStore = findExport(
  (x) => x?.exports?.A?.__proto__?.getStreamerActiveStreamMetadata,
  (m) => m.exports.A,
  "ApplicationStreamingStore",
);
const RunningGameStore = findExport(
  (x) => x?.exports?.Ay?.getRunningGames,
  (m) => m.exports.Ay,
  "RunningGameStore",
);
const QuestsStore = findExport(
  (x) => x?.exports?.A?.__proto__?.getQuest,
  (m) => m.exports.A,
  "QuestsStore",
);
const ChannelStore = findExport(
  (x) => x?.exports?.A?.__proto__?.getAllThreadsForParent,
  (m) => m.exports.A,
  "ChannelStore",
);
const GuildChannelStore = findExport(
  (x) => x?.exports?.Ay?.getSFWDefaultChannel,
  (m) => m.exports.Ay,
  "GuildChannelStore",
);
const FluxDispatcher = findExport(
  (x) => x?.exports?.h?.__proto__?.flushWaitQueue,
  (m) => m.exports.h,
  "FluxDispatcher",
);
const api = findExport(
  (x) => x?.exports?.Bo?.get,
  (m) => m.exports.Bo,
  "API",
);

console.log("[Quest Completer] All modules loaded successfully.");

// ===========================================================================
//  Retry wrapper — retries API calls on failure with exponential backoff
//  Uses .call(api, ...) to preserve the correct `this` context.
// ===========================================================================
async function apiWithRetry(method, options, maxRetries = 3) {
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await api[method].call(api, options);
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
//  Quest helpers
// ===========================================================================
const SUPPORTED_TASKS = [
  "WATCH_VIDEO",
  "PLAY_ON_DESKTOP",
  "STREAM_ON_DESKTOP",
  "PLAY_ACTIVITY",
  "WATCH_VIDEO_ON_MOBILE",
];

const isDesktopApp = typeof DiscordNative !== "undefined";

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function getTaskConfig(quest) {
  return quest?.config?.taskConfig ?? quest?.config?.taskConfigV2 ?? null;
}

function getTaskName(taskConfig) {
  if (!taskConfig?.tasks) return null;
  return SUPPORTED_TASKS.find((task) => taskConfig.tasks[task] != null) ?? null;
}

function getQuestProgress(quest, taskName) {
  if (!quest?.config?.configVersion) return 0;
  if (quest.config.configVersion === 1) {
    return quest.userStatus?.streamProgressSeconds ?? 0;
  }
  return Math.floor(quest.userStatus?.progress?.[taskName]?.value ?? 0);
}

function getQuestContext(quest) {
  const taskConfig = getTaskConfig(quest);
  const taskName = getTaskName(taskConfig);

  if (!taskConfig || !taskName) {
    return null;
  }

  const target = taskConfig.tasks?.[taskName]?.target;
  if (typeof target !== "number") {
    return null;
  }

  return {
    taskConfig,
    taskName,
    secondsNeeded: target,
    secondsDone: getQuestProgress(quest, taskName),
  };
}

function isQuestEligible(quest) {
  const expiresAt = new Date(quest?.config?.expiresAt ?? 0).getTime();
  return Boolean(
    quest?.userStatus?.enrolledAt &&
      !quest?.userStatus?.completedAt &&
      expiresAt > Date.now() &&
      getQuestContext(quest),
  );
}

async function completeVideoQuest(quest, questName, context) {
  const maxFuture = 10;
  const speed = 7;
  const interval = 1;
  const enrolledAt = new Date(quest.userStatus.enrolledAt).getTime();
  let completed = false;

  console.log(
    `[Quest Completer] Spoofing video for "${questName}". ETA: ~${Math.ceil((context.secondsNeeded - context.secondsDone) / speed)} seconds.`,
  );

  while (!completed && context.secondsDone < context.secondsNeeded) {
    const maxAllowed = Math.floor((Date.now() - enrolledAt) / 1000) + maxFuture;
    const progressHeadroom = maxAllowed - context.secondsDone;
    const timestamp = context.secondsDone + speed;

    if (progressHeadroom >= speed) {
      const response = await apiWithRetry("post", {
        url: `/quests/${quest.id}/video-progress`,
        body: {
          timestamp: Math.min(context.secondsNeeded, timestamp + Math.random()),
        },
      });
      completed = response.body.completed_at != null;
      context.secondsDone = Math.min(context.secondsNeeded, timestamp);
    }

    if (context.secondsDone >= context.secondsNeeded) break;
    await sleep(interval * 1000);
  }

  if (!completed) {
    await apiWithRetry("post", {
      url: `/quests/${quest.id}/video-progress`,
      body: { timestamp: context.secondsNeeded },
    });
  }

  console.log(`[Quest Completer] "${questName}" completed!`);
}

function createFakeGame(applicationId, applicationName, exeName, pid) {
  return {
    cmdLine: `C:\\Program Files\\${applicationName}\\${exeName}`,
    exeName,
    exePath: `c:/program files/${applicationName.toLowerCase()}/${exeName}`,
    hidden: false,
    isLauncher: false,
    id: applicationId,
    name: applicationName,
    pid,
    pidPath: [pid],
    processName: applicationName,
    start: Date.now(),
  };
}

function getQuestChannelId() {
  const dmChannel = ChannelStore.getSortedPrivateChannels()?.[0];
  if (dmChannel?.id) {
    return dmChannel.id;
  }

  const guilds = Object.values(GuildChannelStore.getAllGuilds?.() ?? {});
  const guildWithVoice = guilds.find((guild) => guild?.VOCAL?.length > 0);
  return guildWithVoice?.VOCAL?.[0]?.channel?.id ?? null;
}

function waitForHeartbeatProgress(taskName, quest, questName, secondsNeeded) {
  return new Promise((resolve) => {
    const handler = (data) => {
      const progress =
        quest.config.configVersion === 1
          ? data.userStatus?.streamProgressSeconds ?? 0
          : Math.floor(data.userStatus?.progress?.[taskName]?.value ?? 0);
      console.log(`[Quest Completer] ${questName}: ${progress}/${secondsNeeded}s`);
      if (progress >= secondsNeeded) {
        FluxDispatcher.unsubscribe("QUESTS_SEND_HEARTBEAT_SUCCESS", handler);
        resolve();
      }
    };

    FluxDispatcher.subscribe("QUESTS_SEND_HEARTBEAT_SUCCESS", handler);
  });
}

async function completePlayOnDesktop(quest, questName, context, pid) {
  if (!isDesktopApp) {
    console.log(
      `[Quest Completer] PLAY_ON_DESKTOP requires the Discord desktop app. Cannot complete "${questName}" in browser.`,
    );
    return;
  }

  const response = await apiWithRetry("get", {
    url: `/applications/public?application_ids=${quest.config.application.id}`,
  });
  const appData = response.body?.[0];
  if (!appData?.name) {
    throw new Error(`[Quest Completer] Missing application data for "${questName}".`);
  }

  const exeName =
    appData.executables?.find((entry) => entry.os === "win32")?.name?.replace(">", "") ??
    appData.name.replace(/[\/\\:*?"<>|]/g, "");
  const fakeGame = createFakeGame(quest.config.application.id, appData.name, exeName, pid);

  const originalGetRunningGames = RunningGameStore.getRunningGames;
  const originalGetGameForPID = RunningGameStore.getGameForPID;
  const existingGames = RunningGameStore.getRunningGames();

  try {
    RunningGameStore.getRunningGames = () => [fakeGame];
    RunningGameStore.getGameForPID = (gamePid) => [fakeGame].find((game) => game.pid === gamePid);
    FluxDispatcher.dispatch({
      type: "RUNNING_GAMES_CHANGE",
      removed: existingGames,
      added: [fakeGame],
      games: [fakeGame],
    });

    console.log(
      `[Quest Completer] Spoofed game to "${appData.name}". Waiting ~${Math.ceil((context.secondsNeeded - context.secondsDone) / 60)} minutes for "${questName}".`,
    );

    await waitForHeartbeatProgress("PLAY_ON_DESKTOP", quest, questName, context.secondsNeeded);
    console.log(`[Quest Completer] "${questName}" completed!`);
  } finally {
    RunningGameStore.getRunningGames = originalGetRunningGames;
    RunningGameStore.getGameForPID = originalGetGameForPID;
    FluxDispatcher.dispatch({
      type: "RUNNING_GAMES_CHANGE",
      removed: [fakeGame],
      added: [],
      games: [],
    });
  }
}

async function completeStreamOnDesktop(quest, questName, context, pid, applicationName) {
  if (!isDesktopApp) {
    console.log(
      `[Quest Completer] STREAM_ON_DESKTOP requires the Discord desktop app. Cannot complete "${questName}" in browser.`,
    );
    return;
  }

  const originalGetStreamMetadata = ApplicationStreamingStore.getStreamerActiveStreamMetadata;

  try {
    ApplicationStreamingStore.getStreamerActiveStreamMetadata = () => ({
      id: quest.config.application.id,
      pid,
      sourceName: null,
    });

    console.log(
      `[Quest Completer] Spoofed stream to "${applicationName}". Stream any window in VC for ~${Math.ceil((context.secondsNeeded - context.secondsDone) / 60)} minutes.`,
    );
    console.log("[Quest Completer] You need at least 1 other person in the VC!");

    await waitForHeartbeatProgress("STREAM_ON_DESKTOP", quest, questName, context.secondsNeeded);
    console.log(`[Quest Completer] "${questName}" completed!`);
  } finally {
    ApplicationStreamingStore.getStreamerActiveStreamMetadata = originalGetStreamMetadata;
  }
}

async function completePlayActivity(quest, questName, context) {
  const channelId = getQuestChannelId();
  if (!channelId) {
    console.error(
      `[Quest Completer] No DM channels or guild voice channels found. Cannot complete "${questName}".`,
    );
    return;
  }

  const streamKey = `call:${channelId}:1`;
  console.log(
    `[Quest Completer] Completing "${questName}" via activity heartbeats. ETA: ~${Math.ceil((context.secondsNeeded - context.secondsDone) / 60)} minutes.`,
  );

  while (true) {
    const response = await apiWithRetry("post", {
      url: `/quests/${quest.id}/heartbeat`,
      body: { stream_key: streamKey, terminal: false },
    });

    const progress =
      quest.config.configVersion === 1
        ? response.body.progress?.PLAY_ACTIVITY?.value ?? response.body.userStatus?.streamProgressSeconds ?? 0
        : Math.floor(response.body.progress?.PLAY_ACTIVITY?.value ?? 0);
    console.log(`[Quest Completer] ${questName}: ${progress}/${context.secondsNeeded}s`);

    if (progress >= context.secondsNeeded) {
      await apiWithRetry("post", {
        url: `/quests/${quest.id}/heartbeat`,
        body: { stream_key: streamKey, terminal: true },
      });
      break;
    }

    await sleep(20 * 1000);
  }

  console.log(`[Quest Completer] "${questName}" completed!`);
}

async function processQuest(quest) {
  const context = getQuestContext(quest);
  if (!context) {
    console.warn("[Quest Completer] Skipping quest with unsupported or malformed task config.");
    return;
  }

  const questName = quest?.config?.messages?.questName ?? "Unknown quest";
  const applicationId = quest?.config?.application?.id;
  const applicationName = quest?.config?.application?.name ?? "unknown app";
  const pid = Math.floor(Math.random() * 30000) + 1000;

  console.log(
    `[Quest Completer] Processing: "${questName}" | Task: ${context.taskName} | ${context.secondsDone}/${context.secondsNeeded}s done`,
  );

  switch (context.taskName) {
    case "WATCH_VIDEO":
    case "WATCH_VIDEO_ON_MOBILE":
      await completeVideoQuest(quest, questName, context);
      return;
    case "PLAY_ON_DESKTOP":
      await completePlayOnDesktop(quest, questName, context, pid);
      return;
    case "STREAM_ON_DESKTOP":
      await completeStreamOnDesktop(quest, questName, context, pid, applicationName);
      return;
    case "PLAY_ACTIVITY":
      await completePlayActivity(quest, questName, context);
      return;
    default:
      console.warn(
        `[Quest Completer] Unsupported task "${context.taskName}" for "${questName}".`,
      );
  }
}

async function processQuests() {
  const quests = [...(QuestsStore.quests?.values?.() ?? [])].filter(isQuestEligible);

  if (quests.length === 0) {
    console.log("[Quest Completer] No uncompleted quests found!");
    return;
  }

  console.log(`[Quest Completer] Found ${quests.length} uncompleted quest(s).`);

  for (const quest of quests) {
    try {
      await processQuest(quest);
    } catch (err) {
      console.error(
        `[Quest Completer] ERROR completing "${quest?.config?.messages?.questName ?? "Unknown quest"}":`,
        err?.message ?? err,
        err?.stack ?? "",
      );
    }
  }

  console.log("[Quest Completer] All quests processed.");
}

processQuests().catch((err) => {
  console.error("[Quest Completer] Fatal error:", err?.message ?? err, err?.stack ?? "");
});
