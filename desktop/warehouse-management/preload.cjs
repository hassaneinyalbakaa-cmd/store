const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("warehouseDesktop", {
  getServerUrl: () => ipcRenderer.invoke("connection:get"),
  saveServerUrl: (value) => ipcRenderer.invoke("connection:save", value),
  clearServerUrl: () => ipcRenderer.invoke("connection:clear"),
});