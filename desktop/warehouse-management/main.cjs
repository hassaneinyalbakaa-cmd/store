const { app, BrowserWindow, dialog, ipcMain, Menu, shell } = require("electron");
const fs = require("node:fs");
const path = require("node:path");

const CONFIG_FILE = "connection.json";
let mainWindow = null;
let setupWindow = null;

function configPath() {
  return path.join(app.getPath("userData"), CONFIG_FILE);
}

function readServerUrl() {
  try {
    const content = fs.readFileSync(configPath(), "utf8");
    return JSON.parse(content).serverUrl || "";
  } catch {
    return "";
  }
}

function normalizeServerUrl(value) {
  const candidate = String(value || "").trim();
  if (!candidate) {
    throw new Error("أدخل عنوان النظام المركزي.");
  }

  let parsed;
  try {
    parsed = new URL(candidate);
  } catch {
    throw new Error("أدخل عنوانًا صحيحًا مثل https://warehouse.example.com");
  }

  if (!["http:", "https:"].includes(parsed.protocol)) {
    throw new Error("يجب أن يبدأ العنوان بـ http:// أو https://");
  }

  parsed.hash = "";
  return parsed.toString().replace(/\/$/, "");
}

function saveServerUrl(value) {
  const serverUrl = normalizeServerUrl(value);
  fs.mkdirSync(path.dirname(configPath()), { recursive: true });
  fs.writeFileSync(configPath(), JSON.stringify({ serverUrl }, null, 2), "utf8");
  return serverUrl;
}

function createSetupWindow() {
  if (setupWindow && !setupWindow.isDestroyed()) {
    setupWindow.focus();
    return;
  }

  setupWindow = new BrowserWindow({
    width: 560,
    height: 540,
    minWidth: 480,
    minHeight: 460,
    resizable: false,
    title: "إعداد الاتصال — نظام إدارة المخزن",
    backgroundColor: "#f6f5f0",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, "preload.cjs"),
    },
  });
  setupWindow.setMenuBarVisibility(false);
  setupWindow.loadFile(path.join(__dirname, "setup.html"));
  setupWindow.on("closed", () => {
    setupWindow = null;
  });
}

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 1024,
    minHeight: 680,
    title: "نظام إدارة المخزن",
    backgroundColor: "#102c31",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith("http://") || url.startsWith("https://")) {
      shell.openExternal(url);
    }
    return { action: "deny" };
  });
}

async function openConfiguredServer() {
  const serverUrl = readServerUrl();
  if (!serverUrl) {
    createSetupWindow();
    return;
  }

  if (!mainWindow || mainWindow.isDestroyed()) {
    createMainWindow();
  }

  try {
    await mainWindow.loadURL(serverUrl);
  } catch {
    await dialog.showMessageBox(mainWindow, {
      type: "warning",
      title: "تعذر الاتصال",
      message: "تعذر فتح النظام المركزي.",
      detail: `تحقق من العنوان والاتصال بالشبكة:\n${serverUrl}`,
      buttons: ["إعداد الاتصال"],
    });
    createSetupWindow();
  }
}

function buildMenu() {
  Menu.setApplicationMenu(
    Menu.buildFromTemplate([
      {
        label: "النظام",
        submenu: [
          {
            label: "تغيير عنوان الخادم",
            accelerator: "CmdOrCtrl+,",
            click: () => createSetupWindow(),
          },
          {
            label: "إعادة تحميل",
            accelerator: "CmdOrCtrl+R",
            click: () => mainWindow?.reload(),
          },
          { type: "separator" },
          { role: "quit", label: "إغلاق البرنامج" },
        ],
      },
      {
        label: "مساعدة",
        submenu: [
          {
            label: "فتح عنوان الخادم في المتصفح",
            click: () => {
              const serverUrl = readServerUrl();
              if (serverUrl) shell.openExternal(serverUrl);
            },
          },
        ],
      },
    ]),
  );
}

ipcMain.handle("connection:get", () => readServerUrl());
ipcMain.handle("connection:save", async (_event, value) => {
  const serverUrl = saveServerUrl(value);
  if (setupWindow && !setupWindow.isDestroyed()) {
    setupWindow.close();
  }
  await openConfiguredServer();
  return serverUrl;
});
ipcMain.handle("connection:clear", () => {
  try {
    fs.unlinkSync(configPath());
  } catch {
    // The file may not exist on first launch.
  }
  mainWindow?.close();
  createSetupWindow();
});

app.whenReady().then(() => {
  buildMenu();
  openConfiguredServer();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) openConfiguredServer();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});