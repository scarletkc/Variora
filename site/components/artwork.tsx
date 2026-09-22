export function Artwork({ id }: { id: string }) {
  if (id === "rainy-ramen")
    return (
      <div className="artwork ramen" aria-hidden="true">
        <div className="rain-lines" />
        <span className="art-label">雨の夜</span>
        <span className="ramen-sign">
          ラ<br />ー<br />メ<br />ン
        </span>
        <div className="ramen-window">
          <div className="curtain">
            <span />
            <span />
            <span />
            <span />
          </div>
          <div className="steam">
            <i />
            <i />
            <i />
          </div>
          <div className="bowl">
            <div className="noodles" />
            <span />
          </div>
          <div className="chopsticks" />
        </div>
        <div className="art-caption">
          <span>
            RAINY
            <br />
            <strong>RAMEN</strong>
          </span>
          <span className="art-number">01 / SVG</span>
        </div>
      </div>
    );
  if (id === "neon-serpent")
    return (
      <div className="artwork serpent" aria-hidden="true">
        <div className="city-grid" />
        <div className="city-sun" />
        <div className="city-building one" />
        <div className="city-building two" />
        <div className="city-building three" />
        <svg className="snake-path" viewBox="0 0 600 300" fill="none">
          <path
            d="m40 265 155-67 85 35 104-47-90-42 119-58"
            stroke="#91c6a0"
            strokeWidth="23"
            strokeLinejoin="round"
          />
          <path
            d="m40 265 155-67 85 35 104-47-90-42 119-58"
            stroke="#c4efd0"
            strokeWidth="2"
            strokeDasharray="2 15"
          />
          <path d="m413 86 28-11-28-12-27 12Z" fill="#e1ffb2" />
        </svg>
        <span className="art-label">新しい視点</span>
        <div className="art-caption">
          <span>
            NEON
            <br />
            <strong>SERPENT</strong>
          </span>
          <span className="art-number">02 / 3D</span>
        </div>
      </div>
    );
  return (
    <div className="artwork generic" aria-hidden="true">
      <div className="orbit-art">
        <i />
        <i />
        <i />
      </div>
      <span className="art-label">VARIORA / EXPERIMENT</span>
    </div>
  );
}

export function HeroArtwork() {
  return (
    <div className="hero-art" aria-hidden="true">
      <div className="hero-axis horizontal" />
      <div className="hero-axis vertical" />
      <div className="orbit-art">
        <i />
        <i />
        <i />
        <i />
      </div>
      <span className="coordinate top">SAME INPUT</span>
      <span className="coordinate bottom">∞ OUTCOMES</span>
      <span className="orbital-dot" />
    </div>
  );
}
