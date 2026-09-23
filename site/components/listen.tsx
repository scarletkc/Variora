"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState, type CSSProperties } from "react";
import {
  type Model,
  type MusicOutput,
  type Origin,
  type Project,
  fileSource,
  modelSource,
  outputTypes,
  projectSource,
  projects,
} from "@/lib/catalog";
import { messages, type Locale, type Messages } from "@/lib/i18n";
import { Arrow, Download } from "./icons";
import { Comments } from "./comments";

type AudioFile = NonNullable<MusicOutput["audio"]>;

const clock = (seconds: number) => {
  if (!Number.isFinite(seconds)) return "–:––";
  const whole = Math.max(0, Math.floor(seconds));
  const minutes = Math.floor(whole / 60);
  const rest = String(whole % 60).padStart(2, "0");
  return minutes >= 60
    ? `${Math.floor(minutes / 60)}:${String(minutes % 60).padStart(2, "0")}:${rest}`
    : `${minutes}:${rest}`;
};

function Glyph({ name }: { name: "play" | "pause" | "restart" | "volume" }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {name === "play" && <path d="M8 5.5v13l10.5-6.5Z" fill="currentColor" />}
      {name === "pause" && (
        <path d="M8 5v14M16 5v14" strokeWidth="3.2" strokeLinecap="butt" />
      )}
      {name === "restart" && <path d="M4 12a8 8 0 1 0 2.4-5.7M4 4v5h5" />}
      {name === "volume" && (
        <path d="M4 9.5h3.5L12 5.5v13l-4.5-4H4ZM15.5 9a4 4 0 0 1 0 6M18 6.5a7.5 7.5 0 0 1 0 11" />
      )}
    </svg>
  );
}

function Muted() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M4 9.5h3.5L12 5.5v13l-4.5-4H4ZM16 9.5l5 5M21 9.5l-5 5" />
    </svg>
  );
}

function Roll({
  url,
  progress,
  label,
}: {
  url: string;
  progress: number;
  label: string;
}) {
  return (
    <div
      className="player-roll"
      role="img"
      aria-label={label}
      style={
        {
          "--roll": `url("${url}")`,
          "--progress": `${progress * 100}%`,
        } as CSSProperties
      }
    >
      <div>
        <span className="roll-notes" />
        <span className="roll-notes played" />
        {progress > 0 && progress < 1 && <span className="roll-head" />}
      </div>
    </div>
  );
}

const jumps: Record<string, number> = {
  ArrowLeft: -5,
  ArrowDown: -5,
  ArrowRight: 5,
  ArrowUp: 5,
  PageDown: -15,
  PageUp: 15,
};

function Player({
  audio,
  roll,
  span,
  title,
  artist,
  autoPlay,
  volume,
  muted,
  onVolume,
  onMuted,
  onPlaying,
  t,
}: {
  audio: AudioFile;
  roll: string | null;
  span: number;
  title: string;
  artist: string;
  autoPlay: boolean;
  volume: number;
  muted: boolean;
  onVolume: (value: number) => void;
  onMuted: (value: boolean) => void;
  onPlaying: (value: boolean) => void;
  t: Messages;
}) {
  const media = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [time, setTime] = useState(0);
  const [duration, setDuration] = useState(NaN);
  const [failure, setFailure] = useState("");
  const [adjustable, setAdjustable] = useState(true);
  useEffect(() => {
    const element = media.current!;
    let live = true;
    if (!element.canPlayType(audio.type))
      setFailure(t.audioUnsupported.replace("{format}", audio.format));
    else if (element.error) setFailure(t.audioError);
    if (element.readyState >= HTMLMediaElement.HAVE_METADATA)
      setDuration(element.duration);
    const probe = document.createElement("audio");
    probe.volume = 0.5;
    setAdjustable(probe.volume === 0.5);
    const report = () => live && onPlaying(!element.paused);
    element.addEventListener("play", report);
    element.addEventListener("pause", report);
    if (autoPlay) element.play().catch(() => live && onPlaying(false));
    return () => {
      live = false;
      element.removeEventListener("play", report);
      element.removeEventListener("pause", report);
      element.pause();
    };
  }, []);
  useEffect(() => {
    media.current!.volume = volume;
    media.current!.muted = muted;
  }, [volume, muted]);
  useEffect(() => {
    if (!playing) return;
    let frame = 0;
    const tick = () => {
      setTime(media.current?.currentTime ?? 0);
      frame = requestAnimationFrame(tick);
    };
    tick();
    return () => cancelAnimationFrame(frame);
  }, [playing]);

  const ready = Number.isFinite(duration) && duration > 0 && !failure;
  function toggle() {
    const element = media.current!;
    if (element.paused) element.play().catch(() => {});
    else element.pause();
  }
  function seek(value: number) {
    const element = media.current!;
    element.currentTime = Math.max(
      0,
      Number.isFinite(duration) ? Math.min(value, duration) : value,
    );
    setTime(element.currentTime);
  }
  function keys(event: React.KeyboardEvent) {
    if (event.key in jumps) seek(media.current!.currentTime + jumps[event.key]);
    else if (event.key === "Home") seek(0);
    else if (event.key === "End") seek(duration);
    else if (event.key === " " || event.key === "k") toggle();
    else return;
    event.preventDefault();
  }
  const shown = ready ? Math.min(time, duration) : 0;
  const level = muted ? 0 : volume;
  return (
    <div className="player" role="group" aria-label={`${t.audio}: ${artist}`}>
      {roll && (
        <Roll
          url={roll}
          progress={span > 0 ? Math.min(time / span, 1) : 0}
          label={t.pianoRoll}
        />
      )}
      <div className="player-controls">
        <button
          type="button"
          className="player-toggle"
          aria-label={playing ? t.pause : t.play}
          disabled={Boolean(failure)}
          onClick={toggle}
        >
          <Glyph name={playing ? "pause" : "play"} />
        </button>
        <div className="player-seek">
          <span className="player-time">{clock(shown)}</span>
          <input
            type="range"
            className="player-range"
            aria-label={t.seek}
            aria-valuetext={t.timeOf
              .replace("{elapsed}", clock(shown))
              .replace("{total}", clock(duration))}
            min={0}
            max={ready ? duration : 0}
            step={0.1}
            value={shown}
            disabled={!ready}
            style={
              {
                "--fill": `${ready ? (shown / duration) * 100 : 0}%`,
              } as CSSProperties
            }
            onChange={(event) => seek(Number(event.target.value))}
            onKeyDown={keys}
          />
          <span className="player-time">{clock(duration)}</span>
        </div>
        <div className="player-extra">
          <button
            type="button"
            className="player-button"
            disabled={Boolean(failure)}
            onClick={() => {
              seek(0);
              media.current!.play().catch(() => {});
            }}
          >
            <Glyph name="restart" />
            {t.restart}
          </button>
          <div className="player-volume">
            <button
              type="button"
              className="player-icon"
              aria-label={muted ? t.unmute : t.mute}
              onClick={() => onMuted(!muted)}
            >
              {level === 0 ? <Muted /> : <Glyph name="volume" />}
            </button>
            {adjustable && (
              <input
                type="range"
                className="player-range volume"
                aria-label={t.volume}
                aria-valuetext={`${Math.round(level * 100)}%`}
                min={0}
                max={1}
                step={0.05}
                value={level}
                style={{ "--fill": `${level * 100}%` } as CSSProperties}
                onChange={(event) => {
                  onVolume(Number(event.target.value));
                  onMuted(false);
                }}
              />
            )}
          </div>
        </div>
      </div>
      {failure && (
        <p className="player-message" role="alert">
          {failure}
        </p>
      )}
      <audio
        ref={media}
        src={audio.url}
        preload="metadata"
        onLoadedMetadata={(event) => setDuration(event.currentTarget.duration)}
        onDurationChange={(event) => setDuration(event.currentTarget.duration)}
        onTimeUpdate={(event) => setTime(event.currentTarget.currentTime)}
        onPlay={() => {
          setPlaying(true);
          if ("mediaSession" in navigator && "MediaMetadata" in window)
            navigator.mediaSession.metadata = new MediaMetadata({
              title,
              artist,
              album: "Variora",
            });
        }}
        onPause={() => setPlaying(false)}
        onError={() => setFailure(t.audioError)}
      />
    </div>
  );
}

function FileRow({
  kind,
  name,
  origin,
  href,
  download,
  label,
  t,
}: {
  kind: string;
  name: string;
  origin: Origin;
  href: string;
  download?: string;
  label: string;
  t: Messages;
}) {
  return (
    <li>
      <span className="file-label">
        <span className="file-kind">{kind}</span>
        <span className="file-name">{name}</span>
      </span>
      <span className="file-origin">
        {origin === "model" ? t.fromModel : t.fromContributor}
      </span>
      <a
        className="text-link"
        href={href}
        {...(download ? { download } : { target: "_blank", rel: "noreferrer" })}
      >
        {label}
        {download ? <Download /> : <Arrow diagonal />}
      </a>
    </li>
  );
}

function Details({
  project,
  model,
  output,
  locale,
}: {
  project: Project;
  model: Model;
  output: MusicOutput;
  locale: Locale;
}) {
  const t = messages[locale];
  const summary = output.midi?.summary;
  const tempo = summary?.tempo;
  return (
    <div className="listen-details">
      <section className="listen-section" aria-labelledby="listen-files">
        <h2 id="listen-files">{t.files}</h2>
        <ul className="file-list">
          {output.audio && (
            <FileRow
              kind={`${t.audio} · ${output.audio.format}`}
              name={output.audio.name}
              origin={output.audio.origin}
              href={output.audio.url}
              download={output.audio.name}
              label={t.download}
              t={t}
            />
          )}
          {output.midi && (
            <FileRow
              kind="MIDI"
              name={output.midi.name}
              origin={output.midi.origin}
              href={output.midi.url}
              download={output.midi.name}
              label={t.download}
              t={t}
            />
          )}
          {output.source.map((item) => (
            <FileRow
              key={item.path}
              kind={t.sourceCode}
              name={item.directory ? `${item.path}/` : item.path}
              origin={item.origin}
              href={fileSource(project, model, item.path, item.directory)}
              label={t.source}
              t={t}
            />
          ))}
        </ul>
        {!output.source.length && <p className="listen-note">{t.noSource}</p>}
      </section>
      {output.midi && (
        <section className="listen-section" aria-labelledby="listen-midi">
          <h2 id="listen-midi">{t.midiDetails}</h2>
          {summary ? (
            <dl className="midi-facts">
              <div>
                <dt>{t.length}</dt>
                <dd>{clock(summary.duration)}</dd>
              </div>
              {tempo && (
                <div>
                  <dt>{t.tempo}</dt>
                  <dd>
                    {t.bpm.replace(
                      "{value}",
                      tempo.min === tempo.max
                        ? String(tempo.min)
                        : `${tempo.min}–${tempo.max}`,
                    )}
                  </dd>
                </div>
              )}
              {summary.timeSignature && (
                <div>
                  <dt>{t.timeSignature}</dt>
                  <dd>{summary.timeSignature}</dd>
                </div>
              )}
              {summary.key && (
                <div>
                  <dt>{t.key}</dt>
                  <dd>
                    {t[summary.key.mode].replace("{tonic}", summary.key.tonic)}
                  </dd>
                </div>
              )}
              <div>
                <dt>{t.tracks}</dt>
                <dd>{summary.tracks}</dd>
              </div>
              <div>
                <dt>{t.notes}</dt>
                <dd>{summary.notes.toLocaleString(locale)}</dd>
              </div>
              {summary.instruments.length > 0 && (
                <div className="wide">
                  <dt>{t.instruments}</dt>
                  <dd>{summary.instruments.join(", ")}</dd>
                </div>
              )}
              {summary.markers.length > 0 && (
                <div className="wide">
                  <dt>{t.markers}</dt>
                  <dd>
                    <ol className="midi-markers">
                      {summary.markers.map((marker, index) => (
                        <li key={index}>
                          <span>{clock(marker.time)}</span>
                          {marker.text}
                        </li>
                      ))}
                    </ol>
                  </dd>
                </div>
              )}
            </dl>
          ) : (
            <p className="listen-note">{t.midiUnreadable}</p>
          )}
        </section>
      )}
      <section className="listen-section" aria-labelledby="listen-rendering">
        <h2 id="listen-rendering">{t.rendering}</h2>
        <p className="listen-rendering">{output.rendering || t.unspecified}</p>
      </section>
    </div>
  );
}

export function Listen({ locale }: { locale: Locale }) {
  const query = useSearchParams();
  const project = projects.find((item) => item.id === query.get("project"));
  const model = project?.models.find((item) => item.id === query.get("model"));
  const output = model?.output;
  const t = messages[locale];
  const [volume, setVolume] = useState(1);
  const [muted, setMuted] = useState(false);
  const resume = useRef(false);
  useEffect(() => {
    if (!output?.audio) resume.current = false;
  }, [output]);
  const title =
    project && model && output
      ? `${model.name} - ${project.title} - Variora`
      : `${t.listening} - Variora`;
  if (!project || !model || !output)
    return (
      <div className="empty-state">
        <title>{title}</title>
        <h1>{t.invalidListen}</h1>
        <p>{t.invalidPreviewBody}</p>
        <Link className="button primary" href={`/${locale}/`}>
          {t.goHome}
          <Arrow />
        </Link>
      </div>
    );
  const outputs = project.models.filter((item) => item.output);
  const midi = output.midi;
  const span = midi?.summary?.duration ?? 0;
  return (
    <>
      <title>{title}</title>
      <Link className="back-link" href={`/${locale}/projects/${project.id}/`}>
        ← {t.returnProject}
      </Link>
      <div className="preview-heading">
        <div>
          <p className="eyebrow">
            {project.title} / {t.listening}
          </p>
          <h1>{model.name}</h1>
        </div>
        <div className="listen-links">
          {model.preview && (
            <Link
              className="text-link"
              href={`/${locale}/preview/?project=${encodeURIComponent(project.id)}&model=${encodeURIComponent(model.id)}`}
            >
              {t.preview}
              <Arrow />
            </Link>
          )}
          <a
            className="text-link"
            href={`${projectSource(project)}/PROMPT.md`}
            target="_blank"
            rel="noreferrer"
          >
            {t.sharedPrompt}
            <Arrow diagonal />
          </a>
          <a
            className="text-link"
            href={modelSource(project, model)}
            target="_blank"
            rel="noreferrer"
          >
            {t.record}
            <Arrow diagonal />
          </a>
        </div>
      </div>
      <div className={`listen-layout${outputs.length > 1 ? "" : " single"}`}>
        <section className="player-card" aria-label={t.listening}>
          {output.audio ? (
            <Player
              key={model.id}
              audio={output.audio}
              roll={midi?.roll ?? null}
              span={span}
              title={project.title}
              artist={model.name}
              autoPlay={resume.current}
              volume={volume}
              muted={muted}
              onVolume={setVolume}
              onMuted={setMuted}
              onPlaying={(value) => (resume.current = value)}
              t={t}
            />
          ) : (
            <div className="player">
              {midi?.roll && (
                <Roll url={midi.roll} progress={1} label={t.pianoRoll} />
              )}
              <div className="player-empty" role="status">
                <h2>{t.noAudio}</h2>
                <p>{t.noAudioBody}</p>
              </div>
            </div>
          )}
        </section>
        {outputs.length > 1 && (
          <nav className="listen-switcher" aria-labelledby="listen-outputs">
            <h2 id="listen-outputs">{t.sameBrief}</h2>
            <ul>
              {outputs.map((item) => (
                <li key={item.id}>
                  <Link
                    href={`/${locale}/listen/?project=${encodeURIComponent(project.id)}&model=${encodeURIComponent(item.id)}`}
                    aria-current={item.id === model.id ? "page" : undefined}
                    scroll={false}
                  >
                    <span className="switcher-name">{item.name}</span>
                    <span className="switcher-meta">
                      {outputTypes(item, t).join(" · ")}
                    </span>
                    {item.id === model.id && <span className="status-dot" />}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        )}
        <Details
          project={project}
          model={model}
          output={output}
          locale={locale}
        />
      </div>
      <section className="comments" aria-labelledby="comments-title">
        <h2 id="comments-title">{t.comments}</h2>
        <Comments term={`${project.id}/${model.id}`} locale={locale} />
      </section>
    </>
  );
}
