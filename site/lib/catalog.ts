import data from "@/.generated/catalog.json";
import type { Locale, Messages } from "./i18n";

export type Origin = "model" | "contributor";
export type OutputFile = {
  path: string;
  name: string;
  url: string;
  origin: Origin;
};
export type MidiSummary = {
  format: number;
  tracks: number;
  ticksPerQuarter: number | null;
  duration: number;
  tempo: { min: number; max: number } | null;
  timeSignature: string | null;
  key: { tonic: string; mode: "major" | "minor" } | null;
  notes: number;
  instruments: string[];
  markers: { time: number; text: string }[];
};
export type MusicOutput = {
  type: "music";
  audio: (OutputFile & { format: string; type: string }) | null;
  midi:
    (OutputFile & { summary: MidiSummary | null; roll: string | null }) | null;
  source: { path: string; directory: boolean; origin: Origin }[];
  rendering: string;
};
export type Model = {
  id: string;
  name: string;
  provider: string;
  reasoning: string;
  harness: string;
  firstCommittedAt: string | null;
  author: { name: string; login: string | null } | null;
  commit: string | null;
  preview: string | null;
  screenshot: string | null;
  output: MusicOutput | null;
};
export type Project = {
  id: string;
  title: string;
  description: string;
  category: string;
  summaries: Partial<Record<Locale, string>>;
  models: Model[];
};
export const categories = [
  "illustration",
  "game",
  "music",
  "experiment",
] as const;
export type Category = (typeof categories)[number];
export const projects = data as Project[];
export const repository = "https://github.com/scarletkc/variora";
export const siteUrl = "https://variora.fog.moe";
export const projectSource = (project: Project) =>
  `${repository}/tree/main/projects/${encodeURIComponent(project.id)}`;
export const modelSource = (project: Project, model: Model) =>
  `${projectSource(project)}/models/${encodeURIComponent(model.id)}`;
export const fileSource = (
  project: Project,
  model: Model,
  file: string,
  directory = false,
) =>
  `${repository}/${directory ? "tree" : "blob"}/main/projects/${[project.id, "models", model.id, ...file.split("/")].map(encodeURIComponent).join("/")}`;
export const summary = (project: Project, locale: Locale) =>
  project.summaries[locale] || project.summaries.en || project.description;
export const isCategory = (value: string): value is Category =>
  categories.includes(value as Category);
export const outputTypes = (model: Model, t: Messages) =>
  [
    model.output?.audio && `${t.audio} (${model.output.audio.format})`,
    model.output?.midi && "MIDI",
    model.output?.source.length && t.sourceCode,
    model.preview && t.webPreview,
  ].filter((value): value is string => Boolean(value));
