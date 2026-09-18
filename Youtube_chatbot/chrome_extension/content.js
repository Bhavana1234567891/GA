/**
 * Content script: injected into YouTube watch pages.
 * Listens for SEEK_VIDEO messages and jumps the player to the given time.
 */

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "SEEK_VIDEO" && typeof message.seconds === "number") {
    const video = document.querySelector("video");
    if (video) {
      video.currentTime = message.seconds;
      video.play();
    }
  }
});
