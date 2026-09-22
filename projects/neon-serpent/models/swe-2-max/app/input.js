// Keyboard + pointer-lock mouse + touch steering.
export class Input {
  constructor(canvas) {
    this.canvas = canvas;
    this.keys = new Set();
    this.actions = new Set();   // edge-triggered: pause, restart, mute, any
    this.lookDX = 0;            // accumulated pointer delta (radians scale later)
    this.touchSteer = 0;        // -1..1 from touch drag
    this.touchBoost = false;
    this.isTouch = matchMedia("(pointer: coarse)").matches;
    this._lastTX = null;

    addEventListener("keydown", (e) => {
      if (e.repeat) return;
      this.keys.add(e.code);
      this.actions.add("any");
      if (e.code === "KeyP" || e.code === "Escape") this.actions.add("pause");
      if (e.code === "KeyR") this.actions.add("restart");
      if (e.code === "KeyM") this.actions.add("mute");
      if (["Space", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(e.code))
        e.preventDefault();
    });
    addEventListener("keyup", (e) => this.keys.delete(e.code));
    addEventListener("blur", () => this.keys.clear());

    document.addEventListener("mousemove", (e) => {
      if (document.pointerLockElement === canvas) {
        this.lookDX += e.movementX;
      }
    });
    document.addEventListener("pointerlockchange", () => {
      if (document.pointerLockElement !== canvas) this.actions.add("unlock");
    });

    // Touch: horizontal drag steers; the boost button is a DOM element.
    const opts = { passive: false };
    canvas.addEventListener("touchstart", (e) => {
      e.preventDefault();
      this._lastTX = e.touches[0].clientX;
      this.actions.add("any");
    }, opts);
    canvas.addEventListener("touchmove", (e) => {
      e.preventDefault();
      const x = e.touches[0].clientX;
      if (this._lastTX != null) {
        this.touchSteer = Math.max(-1, Math.min(1,
          this.touchSteer + (x - this._lastTX) / 70));
      }
      this._lastTX = x;
    }, opts);
    canvas.addEventListener("touchend", (e) => {
      e.preventDefault();
      this._lastTX = null;
      this.touchSteer *= 0.4;
    }, opts);
  }

  lock() {
    if (this.isTouch) return;
    try {
      const p = this.canvas.requestPointerLock?.();
      p?.catch?.(() => {});
    } catch { /* pointer lock unsupported */ }
  }
  unlock() {
    if (document.pointerLockElement) document.exitPointerLock();
  }
  get locked() {
    return document.pointerLockElement === this.canvas;
  }

  /** Analog steering from keys and touch, -1..1. */
  turnAxis() {
    const k = (this.keys.has("KeyD") || this.keys.has("ArrowRight") ? 1 : 0)
      - (this.keys.has("KeyA") || this.keys.has("ArrowLeft") ? 1 : 0);
    return Math.max(-1, Math.min(1, k + this.touchSteer));
  }

  /** Heading delta accumulated from the pointer, in radians. */
  consumeLook() {
    const dx = this.lookDX;
    this.lookDX = 0;
    return dx * 0.0026;
  }

  get boost() {
    return this.keys.has("ShiftLeft") || this.keys.has("ShiftRight")
      || this.keys.has("KeyW") || this.keys.has("Space") || this.touchBoost;
  }

  consume(action) {
    const had = this.actions.has(action);
    this.actions.delete(action);
    return had;
  }
}
