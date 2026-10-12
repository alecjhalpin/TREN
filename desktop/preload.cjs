'use strict';
const {contextBridge,ipcRenderer}=require('electron');
contextBridge.exposeInMainWorld('desktopChrome',Object.freeze({
 theme:mode=>ipcRenderer.send('chrome-theme',mode),
 menu:()=>ipcRenderer.send('chrome-menu'),
 update:()=>ipcRenderer.invoke('unified-update'),
 setup:feature=>ipcRenderer.invoke('optional-setup',feature)
}));
window.addEventListener('DOMContentLoaded',()=>document.body.classList.add('is-desktop'));
