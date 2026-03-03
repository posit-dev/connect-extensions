const w = window as Window & { __CONNECT_ROOT_PATH__?: string };
export const apiBase = (w.__CONNECT_ROOT_PATH__ ?? "").replace(/\/$/, "");
