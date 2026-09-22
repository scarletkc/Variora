import data from "@/.generated/catalog.json";
import type { Locale } from "./i18n";

export type Model = {
  id: string;
  name: string;
  provider: string;
  harness: string;
  preview: string | null;
};
export type Project = {
  id: string;
  title: string;
  description: string;
  category: string;
  summaries: Partial<Record<Locale, string>>;
  models: Model[];
};
export const projects = data as Project[];
export const repository = "https://github.com/scarletkc/variora";
export const siteUrl = "https://variora.fog.moe";
export const projectSource = (project: Project) =>
  `${repository}/tree/main/projects/${encodeURIComponent(project.id)}`;
export const modelSource = (project: Project, model: Model) =>
  `${projectSource(project)}/models/${encodeURIComponent(model.id)}`;
export const summary = (project: Project, locale: Locale) =>
  project.summaries[locale] || project.summaries.en || project.description;
