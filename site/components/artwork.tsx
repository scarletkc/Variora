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
  if (id === "pelican-cycle")
    return (
      <div className="artwork pelican" aria-hidden="true">
        <svg
          className="pelican-scene"
          viewBox="0 0 600 360"
          fill="none"
          preserveAspectRatio="xMidYMid slice"
        >
          <circle cx="132" cy="91" r="39" fill="#e8bd7a" />
          <circle cx="132" cy="91" r="48" stroke="#e8bd7a" opacity="0.2" />
          <path
            d="M0 185Q65 160 123 180Q182 132 241 181Q301 161 363 184Q474 161 600 177V280H0Z"
            fill="#3f6969"
          />
          <path d="M0 202H600V287H0Z" fill="#31595e" />
          <path
            d="M18 218H95M126 237H211M206 213H256M449 229H520M536 213H584"
            stroke="#8eafa0"
            strokeWidth="2"
            strokeLinecap="round"
            opacity="0.45"
          />
          <path d="M0 271Q139 249 284 274T600 260V360H0Z" fill="#243c38" />
          <path
            d="M0 291Q143 268 279 291T600 281"
            stroke="#b4a27b"
            strokeWidth="2"
            opacity="0.35"
          />
          <ellipse
            cx="372"
            cy="292"
            rx="139"
            ry="9"
            fill="#172d2e"
            opacity="0.7"
          />
          <g strokeLinecap="round" strokeLinejoin="round">
            {[287, 459].map((x) => (
              <g key={x} transform={`translate(${x} 246)`}>
                <circle r="44" stroke="#162c30" strokeWidth="8" />
                <circle r="39" stroke="#b9c6b2" strokeWidth="2" />
                <path
                  d="M-37 0H37M0-37V37M-26-26L26 26M-26 26L26-26M-34-14L34 14M-14-34L14 34"
                  stroke="#93afa6"
                  opacity="0.65"
                />
                <circle r="5" fill="#e6d3a5" stroke="#203c3d" strokeWidth="2" />
              </g>
            ))}
            <path
              d="M287 246L329 190L361 246ZM329 190H424L361 246M424 190L459 246"
              stroke="#1b3438"
              strokeWidth="9"
            />
            <path
              d="M287 246L329 190L361 246ZM329 190H424L361 246M424 190L459 246"
              stroke="#d8a361"
              strokeWidth="5"
            />
            <path
              d="M328 190L323 180M424 190L418 170L441 164"
              stroke="#c6cdb7"
              strokeWidth="4"
            />
            <path
              d="M311 179H338M435 165L444 162"
              stroke="#172e31"
              strokeWidth="7"
            />
            <circle
              cx="361"
              cy="246"
              r="10"
              fill="#738d7e"
              stroke="#1b3438"
              strokeWidth="3"
            />
            <path
              d="M351 234L372 259M363 261H382"
              stroke="#d9c9a3"
              strokeWidth="4"
            />
            <path
              d="M340 183L360 211L371 254"
              stroke="#263b35"
              strokeWidth="9"
            />
            <path
              d="M340 183L360 211L371 254"
              stroke="#dca969"
              strokeWidth="5"
            />
            <path
              d="M370 253L381 257L363 257"
              fill="#e4b975"
              stroke="#e4b975"
              strokeWidth="4"
            />
            <path
              d="M299 158L270 151L283 170L269 170L301 181Z"
              fill="#b9c3ac"
              stroke="#24403f"
              strokeWidth="2"
            />
            <path
              d="M292 161Q301 132 334 139Q351 146 359 141Q372 132 369 113Q366 88 385 79Q403 72 413 85Q424 101 410 113Q397 122 395 141Q393 165 373 181Q349 200 317 187Q292 179 292 161Z"
              fill="#efe9d4"
              stroke="#24403f"
              strokeWidth="2.5"
            />
            <path
              d="M305 177Q335 195 366 173Q387 156 384 140Q382 122 399 111Q412 102 414 91Q424 104 410 113Q397 122 395 141Q393 165 373 181Q347 199 317 187Z"
              fill="#c4cdb7"
            />
            <path
              d="M408 98L505 113Q477 145 447 134Q421 125 407 109Z"
              fill="#d99c56"
              stroke="#24403f"
              strokeWidth="2.5"
            />
            <path
              d="M408 94Q451 96 505 109L511 113L409 107Z"
              fill="#edc17b"
              stroke="#24403f"
              strokeWidth="2.5"
            />
            <circle cx="399" cy="92" r="3" fill="#203b3b" />
            <path d="M395 83L403 82" stroke="#24403f" strokeWidth="2" />
            <path
              d="M340 154Q366 153 389 169L430 163L433 169L388 181Q360 174 340 164Z"
              fill="#d5dcc7"
              stroke="#24403f"
              strokeWidth="2.5"
            />
            <path
              d="M314 153Q337 141 361 164L376 174Q348 189 321 174Q307 165 314 153Z"
              fill="#e8e5ce"
              stroke="#24403f"
              strokeWidth="2.5"
            />
            <path
              d="M321 158Q338 175 362 175M320 166Q331 176 342 178"
              stroke="#8da391"
              strokeWidth="2"
            />
          </g>
        </svg>
        <span className="art-label">COASTAL ROUTE</span>
        <div className="art-caption">
          <span>
            PELICAN
            <br />
            <strong>CYCLE</strong>
          </span>
          <span className="art-number">03 / SVG</span>
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
