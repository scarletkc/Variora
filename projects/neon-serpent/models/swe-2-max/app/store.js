// localStorage is unavailable in sandboxed iframes (opaque origin) and can
// throw in other contexts — degrade to in-memory state instead of crashing.
const memory = new Map();
export const store = {
  get(key) {
    try {
      return localStorage.getItem(key);
    } catch {
      return memory.get(key) ?? null;
    }
  },
  set(key, value) {
    memory.set(key, value);
    try {
      localStorage.setItem(key, value);
    } catch { /* storage unavailable */ }
  },
};
