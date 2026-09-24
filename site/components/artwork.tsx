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
  if (id === "seaside-stroll")
    return (
      <div className="artwork seaside" aria-hidden="true">
        <svg
          className="seaside-scene"
          viewBox="0 0 600 360"
          fill="none"
          preserveAspectRatio="xMidYMid slice"
        >
          <defs>
            <linearGradient id="seaside-sky" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stopColor="#34466b" />
              <stop offset="0.6" stopColor="#8f82a3" />
              <stop offset="1" stopColor="#e8b89b" />
            </linearGradient>
            <linearGradient id="seaside-sea" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stopColor="#58709a" />
              <stop offset="1" stopColor="#1f3049" />
            </linearGradient>
            <linearGradient
              id="seaside-staff"
              x1="0"
              y1="0"
              x2="600"
              y2="0"
              gradientUnits="userSpaceOnUse"
            >
              <stop offset="0" stopColor="#fbeedf" stopOpacity="0" />
              <stop offset="0.12" stopColor="#fbeedf" stopOpacity="0.55" />
              <stop offset="0.8" stopColor="#fbeedf" stopOpacity="0.55" />
              <stop offset="0.96" stopColor="#fbeedf" stopOpacity="0" />
            </linearGradient>
          </defs>
          <rect width="600" height="240" fill="url(#seaside-sky)" />
          <circle cx="452" cy="236" r="58" fill="#f8d9b4" opacity="0.16" />
          <circle cx="452" cy="236" r="34" fill="#f9dfbd" />
          <path
            d="M-20 196Q26 180 66 188Q100 174 138 188Q164 182 182 192Q112 202 40 200Z"
            fill="#f3d5c4"
            opacity="0.4"
          />
          <path
            d="M300 206Q330 192 362 200Q390 190 420 202Q380 212 318 210Z"
            fill="#f3d5c4"
            opacity="0.3"
          />
          <path
            d="M214 46l8 5 8-5M242 60l6 4 6-4"
            stroke="#f5e4d6"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
            opacity="0.75"
          />
          <path
            d="M0 236V214Q30 200 64 206Q96 192 128 210Q152 222 172 236Z"
            fill="#46587c"
          />
          <path d="M82 180h8l3 26h-14Z" fill="#e6dccf" />
          <path d="M80 180h12l-6-8Z" fill="#b8676a" />
          <rect x="84" y="184" width="4" height="4" fill="#f9dfbd" />
          <rect y="236" width="600" height="124" fill="url(#seaside-sea)" />
          <path
            d="M420 248h64M432 258h40M414 270h76M440 282h24"
            stroke="#f9dfbd"
            strokeWidth="2.4"
            strokeLinecap="round"
            opacity="0.5"
          />
          <path
            d="M40 254h44M150 250h70M236 262h36"
            stroke="#9fb2cf"
            strokeWidth="1.6"
            strokeLinecap="round"
            opacity="0.35"
          />
          <g stroke="url(#seaside-staff)" strokeWidth="1.3">
            {[0, 9, 18, 27, 36].map((y) => (
              <path
                key={y}
                d={`M-10 ${132 + y}C120 ${96 + y} 250 ${150 + y} 380 ${112 + y}S560 ${70 + y} 620 ${84 + y}`}
              />
            ))}
          </g>
          <g fill="#fbeedf" stroke="#fbeedf" strokeWidth="2">
            <ellipse
              cx="100"
              cy="137"
              rx="7"
              ry="5"
              stroke="none"
              transform="rotate(-22 100 137)"
            />
            <path d="M106 135V101" />
            <ellipse
              cx="172"
              cy="149"
              rx="7"
              ry="5"
              stroke="none"
              transform="rotate(-22 172 149)"
            />
            <ellipse
              cx="208"
              cy="142"
              rx="7"
              ry="5"
              stroke="none"
              transform="rotate(-22 208 142)"
            />
            <path d="M178 147V115M214 140V108" />
            <path d="M177 115L215 108V114L177 121Z" stroke="none" />
            <ellipse
              cx="300"
              cy="139"
              rx="7"
              ry="5"
              stroke="none"
              transform="rotate(-22 300 139)"
            />
            <path d="M306 137V104Q318 110 318 124" fill="none" />
            <ellipse
              cx="470"
              cy="111"
              rx="7"
              ry="5"
              stroke="none"
              transform="rotate(-22 470 111)"
            />
            <path d="M476 109V76" />
            <ellipse
              cx="520"
              cy="84"
              rx="7"
              ry="5"
              stroke="none"
              transform="rotate(-22 520 84)"
            />
            <path d="M514 86V118" />
          </g>
          <path d="M290 360L600 322V360Z" fill="#15223a" />
          <path
            d="M318 344L600 309M340 341.3V353.9M380 336.3V349M420 331.3V344.1M460 326.4V339.2M500 321.4V334.3M540 316.4V329.4M580 311.5V324.5"
            stroke="#15223a"
            strokeWidth="2.5"
            strokeLinecap="round"
          />
        </svg>
        <span className="art-label">海辺の散歩</span>
        <div className="art-caption">
          <span>
            SEASIDE
            <br />
            <strong>STROLL</strong>
          </span>
          <span className="art-number">04 / MIDI</span>
        </div>
      </div>
    );
  if (id === "christmas-eve")
    return (
      <div className="artwork christmas" aria-hidden="true">
        <svg
          className="christmas-scene"
          viewBox="0 0 600 360"
          fill="none"
          preserveAspectRatio="xMidYMid slice"
        >
          <defs>
            <linearGradient id="christmas-sky" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stopColor="#141b36" />
              <stop offset="0.55" stopColor="#2b3563" />
              <stop offset="1" stopColor="#5d5582" />
            </linearGradient>
            <radialGradient id="christmas-glow">
              <stop offset="0" stopColor="#f2b37c" stopOpacity="0.5" />
              <stop offset="1" stopColor="#f2b37c" stopOpacity="0" />
            </radialGradient>
            <linearGradient id="christmas-ground" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stopColor="#343f6d" />
              <stop offset="1" stopColor="#121831" />
            </linearGradient>
            <linearGradient
              id="christmas-rim"
              x1="0"
              y1="0"
              x2="600"
              y2="0"
              gradientUnits="userSpaceOnUse"
            >
              <stop offset="0.5" stopColor="#cfd7f1" stopOpacity="0" />
              <stop offset="0.68" stopColor="#cfd7f1" stopOpacity="0.45" />
            </linearGradient>
            <radialGradient id="christmas-spill">
              <stop offset="0" stopColor="#f6c77e" stopOpacity="0.4" />
              <stop offset="1" stopColor="#f6c77e" stopOpacity="0" />
            </radialGradient>
            <linearGradient
              id="christmas-staff"
              x1="0"
              y1="0"
              x2="600"
              y2="0"
              gradientUnits="userSpaceOnUse"
            >
              <stop offset="0" stopColor="#eef0fb" stopOpacity="0" />
              <stop offset="0.1" stopColor="#eef0fb" stopOpacity="0.5" />
              <stop offset="0.82" stopColor="#eef0fb" stopOpacity="0.5" />
              <stop offset="0.96" stopColor="#eef0fb" stopOpacity="0" />
            </linearGradient>
          </defs>
          <rect width="600" height="262" fill="url(#christmas-sky)" />
          <ellipse
            cx="440"
            cy="238"
            rx="230"
            ry="120"
            fill="url(#christmas-glow)"
          />
          <circle cx="318" cy="40" r="11" fill="#fbe7b8" opacity="0.15" />
          <path
            d="M318 27L320.5 37.5L331 40L320.5 42.5L318 53L315.5 42.5L305 40L315.5 37.5Z"
            fill="#fbe7b8"
          />
          <g fill="#f7f1de" opacity="0.8">
            {[
              [176, 62],
              [256, 28],
              [372, 70],
              [430, 22],
              [470, 40],
            ].map(([x, y]) => (
              <circle key={x} cx={x} cy={y} r="1.1" />
            ))}
          </g>
          <g fill="#28305c">
            {[
              [0, 228, 30],
              [28, 216, 24],
              [52, 232, 32],
              [84, 208, 20],
              [104, 222, 30],
              [134, 234, 36],
              [170, 214, 26],
              [196, 226, 32],
              [228, 202, 22],
              [250, 220, 30],
              [280, 210, 24],
              [420, 230, 34],
              [520, 226, 30],
            ].map(([x, top, width]) => (
              <rect key={x} x={x} y={top} width={width} height={256 - top} />
            ))}
          </g>
          <path
            d="M34 222h3v4h-3ZM90 214h3v4h-3ZM90 224h3v4h-3ZM176 220h3v4h-3ZM234 208h3v4h-3ZM234 218h3v4h-3ZM258 226h3v4h-3ZM286 216h3v4h-3Z"
            fill="#f3c98a"
            opacity="0.6"
          />
          <g stroke="url(#christmas-staff)" strokeWidth="1.3">
            {[0, 8, 16, 24, 32].map((y) => (
              <path key={y} d={`M-10 ${64 + y}Q300 ${184 + y} 610 ${64 + y}`} />
            ))}
          </g>
          {[
            [80, 118],
            [140, 128],
            [180, 127],
            [250, 142],
            [350, 130],
            [410, 128],
            [445, 123],
            [520, 106],
          ].map(([x, y]) => (
            <g key={x}>
              <circle cx={x} cy={y} r="11" fill="#f7c979" opacity="0.22" />
              <ellipse
                cx={x}
                cy={y}
                rx="6.5"
                ry="4.6"
                fill="#f8d892"
                transform={`rotate(-22 ${x} ${y})`}
              />
            </g>
          ))}
          <g stroke="#f8d892" strokeWidth="2">
            <path d="M86 116V84M146 126V94M186 125V93M256 140V108M356 128V96M416 126V92M451 121V88M526 104V72M356 96Q368 102 367 116" />
            <path
              d="M146 94L186 93V99L146 100ZM416 92L451 88V94L416 98Z"
              fill="#f8d892"
              stroke="none"
            />
          </g>
          <rect x="296" y="214" width="56" height="42" fill="#1b2243" />
          <path d="M288 216L324 186L360 216Z" fill="#232b52" />
          <rect x="398" y="176" width="9" height="20" fill="#171e3c" />
          <rect x="356" y="200" width="60" height="56" fill="#171e3c" />
          <path d="M348 202L386 170L424 202Z" fill="#20284c" />
          <rect x="548" y="218" width="60" height="38" fill="#1b2243" />
          <path d="M540 220L580 190L620 220Z" fill="#232b52" />
          <path
            d="M290 215L324 187L358 215M350 201L386 171L422 201M542 219L580 191L618 219"
            stroke="#e6eaf7"
            strokeWidth="5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <rect x="396" y="173" width="13" height="5" rx="2.5" fill="#e6eaf7" />
          <path
            d="M305 225h13v13h-13ZM330 225h13v13h-13ZM362 216h10v12h-10ZM400 216h10v12h-10ZM378 234V219a8 8 0 0 1 16 0V234ZM560 229h12v12h-12ZM584 229h12v12h-12Z"
            fill="#f6c77e"
          />
          <path
            d="M311.5 225V238M305 231.5H318M336.5 225V238M330 231.5H343M386 211V234M378 224H394M566 229V241M560 235H572M590 229V241M584 235H596"
            stroke="#182040"
            strokeWidth="1.4"
          />
          <rect x="487" y="234" width="10" height="24" fill="#2a2233" />
          <g fill="#1c393d">
            <path d="M492 190L453 238H531Z" />
            <path d="M492 172L463 210H521Z" />
            <path d="M492 158L471 186H513Z" />
          </g>
          <path
            d="M475 181Q492 189 509 179M467 204Q492 214 517 202M458 231Q492 243 526 229"
            stroke="#f8d892"
            strokeWidth="1.2"
            opacity="0.7"
          />
          <g fill="#ffe2a3">
            {[
              [484, 184],
              [492, 208.5],
              [468, 234],
              [502, 235.6],
            ].map(([x, y]) => (
              <circle key={x} cx={x} cy={y} r="2.2" />
            ))}
          </g>
          <g fill="#f2907f">
            {[
              [500, 183],
              [477, 207],
              [507, 206],
              [485, 236.4],
              [518, 232],
            ].map(([x, y]) => (
              <circle key={x} cx={x} cy={y} r="2.2" />
            ))}
          </g>
          <circle cx="492" cy="152" r="13" fill="#ffd98a" opacity="0.22" />
          <path
            d="M492 144L494 149.2L499.6 149.5L495.2 153.1L496.7 158.5L492 155.4L487.3 158.5L488.8 153.1L484.4 149.5L490 149.2Z"
            fill="#ffdf8f"
          />
          <path
            d="M0 248C90 236 200 244 300 250S500 254 600 246V360H0Z"
            fill="url(#christmas-ground)"
          />
          <path
            d="M0 248C90 236 200 244 300 250S500 254 600 246"
            stroke="url(#christmas-rim)"
            strokeWidth="2"
          />
          <g fill="url(#christmas-spill)">
            <ellipse cx="324" cy="263" rx="50" ry="10" />
            <ellipse cx="386" cy="265" rx="46" ry="10" />
            <ellipse cx="578" cy="263" rx="40" ry="9" />
          </g>
          <path
            d="M34 286h62M142 304h86M300 280h46M396 298h74M520 318h46"
            stroke="#8a95c2"
            strokeWidth="1.6"
            strokeLinecap="round"
            opacity="0.25"
          />
          <path
            d="M60 165V179M53.9 168.5L66.1 175.5M53.9 175.5L66.1 168.5M408 56V68M402.8 59L413.2 65M402.8 65L413.2 59"
            stroke="#eef1ff"
            strokeWidth="1.4"
            strokeLinecap="round"
            opacity="0.75"
          />
          <g fill="#f4f6ff" opacity="0.85">
            {[
              [18, 108, 1.8],
              [36, 72, 1.4],
              [52, 188, 2.2],
              [64, 140, 1.6],
              [88, 44, 1.2],
              [104, 212, 1.5],
              [122, 160, 2.4],
              [140, 70, 1.8],
              [162, 118, 1.3],
              [178, 196, 1.9],
              [196, 44, 2.1],
              [214, 150, 1.5],
              [232, 96, 1.2],
              [248, 186, 2.3],
              [266, 58, 1.6],
              [282, 132, 2],
              [300, 206, 1.4],
              [318, 80, 1.3],
              [336, 166, 1.8],
              [352, 104, 2.4],
              [370, 44, 1.5],
              [388, 148, 1.3],
              [404, 90, 2],
              [420, 182, 1.6],
              [436, 118, 1.2],
              [452, 58, 2.2],
              [468, 210, 1.5],
              [486, 92, 1.4],
              [506, 132, 1.9],
              [524, 40, 1.3],
              [540, 172, 2.1],
              [556, 110, 1.5],
              [574, 196, 1.8],
              [590, 140, 1.3],
              [28, 300, 1.6],
              [120, 330, 1.3],
              [210, 288, 1.9],
              [268, 340, 1.4],
              [350, 312, 2],
              [430, 286, 1.5],
              [470, 338, 1.2],
              [520, 300, 1.7],
            ].map(([x, y, r]) => (
              <circle key={`${x} ${y}`} cx={x} cy={y} r={r} />
            ))}
          </g>
        </svg>
        <span className="art-label">聖なる夜</span>
        <div className="art-caption">
          <span>
            CHRISTMAS
            <br />
            <strong>EVE</strong>
          </span>
          <span className="art-number">05 / MIDI</span>
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
