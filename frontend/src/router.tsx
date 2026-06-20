import {
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
} from "@tanstack/react-router";
import { Admin } from "@/pages/Admin";
import { Compare } from "@/pages/Compare";
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

export const compareRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/compare/$user1/$user2",
  component: Compare,
});

export const adminRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/admin",
  component: Admin,
});

const routeTree = rootRoute.addChildren([homeRoute, profileRoute, compareRoute, adminRoute]);

export const router = createRouter({ routeTree });

/* ─── Type safety ────────────────────────────────────────── */
declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
