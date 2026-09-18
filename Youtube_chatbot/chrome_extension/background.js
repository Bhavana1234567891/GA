/**
 * Service worker: extracts video_id from active tab and stores it.
 */

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (tab.url && tab.url.includes("youtube.com/watch")) {
    const url = new URL(tab.url);
    const videoId = url.searchParams.get("v");
    if (videoId) {
      chrome.storage.local.set({ videoId, tabId });
    }
  }
});

chrome.tabs.onActivated.addListener(async (activeInfo) => {
  const tab = await chrome.tabs.get(activeInfo.tabId);
  if (tab.url && tab.url.includes("youtube.com/watch")) {
    const url = new URL(tab.url);
    const videoId = url.searchParams.get("v");
    if (videoId) {
      chrome.storage.local.set({ videoId, tabId: tab.id });
    }
  }
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "GET_VIDEO_ID") {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const tab = tabs[0];
      if (tab && tab.url && tab.url.includes("youtube.com/watch")) {
        const url = new URL(tab.url);
        const videoId = url.searchParams.get("v");
        sendResponse({ videoId, tabId: tab.id });
      } else {
        sendResponse({ videoId: null });
      }
    });
    return true;
  }

  if (message.type === "SEEK_VIDEO") {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]) {
        chrome.tabs.sendMessage(tabs[0].id, {
          type: "SEEK_VIDEO",
          seconds: message.seconds,
        });
      }
    });
  }
});
