import beepSrc from "@/assets/beep.mp3";

const audio = new Audio(beepSrc);
audio.volume = 0.7;

export function playBeep() {
  audio.currentTime = 0;
  audio.play().catch(() => {});
}
