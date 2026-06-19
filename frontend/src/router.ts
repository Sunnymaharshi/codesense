import {
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
} from "@tanstack/react-router";
import { Home } from "@/pages/Home";
import { Profile } from "@/pages/Profile";

/* ─── Root layout ────────────────────────────────────────── */
const rootRoute = createRootRoute({
  component: Outlet,
});

/* ─── Routes ─────────────────────────────────────────────── */
export const homeRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: Home,
});

export const profileRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/u/$username",
  component: Profile,
});

const routeTree = rootRoute.addChildren([homeRoute, profileRoute]);

export const router = createRouter({ routeTree });

/* ─── Type safety ────────────────────────────────────────── */
declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
