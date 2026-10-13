// Keep this out of "use client" modules: a server layout importing it from one
// receives a client reference, so <head> suspends during hydration.
export const themeScript = `(()=>{let t='system';try{t=localStorage.getItem('variora-theme')||t}catch{}document.documentElement.dataset.theme=t==='dark'||(t!=='light'&&matchMedia('(prefers-color-scheme: dark)').matches)?'dark':'light'})()`;
