import { createRouter, createWebHistory } from "vue-router";
import UserLayout from "../layouts/UserLayout.vue";
import AdminLayout from "../layouts/AdminLayout.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", component: () => import("../views/Login.vue") },
    { path: "/register", component: () => import("../views/Register.vue") },
    {
      path: "/",
      component: UserLayout,
      meta: { auth: true },
      children: [
        { path: "", redirect: "/products" },
        { path: "products", component: () => import("../views/Products.vue") },
        { path: "products/:id", component: () => import("../views/ProductDetail.vue") },
        { path: "behaviors", component: () => import("../views/Behaviors.vue") },
        { path: "predict", redirect: "/predictions" },
        { path: "predictions", component: () => import("../views/PredictList.vue") },
        { path: "predictions/:id", component: () => import("../views/PredictDetail.vue") },
        { path: "analysis", component: () => import("../views/Analysis.vue") },
        { path: "profile", component: () => import("../views/Profile.vue") },
      ],
    },
    {
      path: "/admin",
      component: AdminLayout,
      meta: { auth: true, admin: true },
      children: [
        { path: "", redirect: "/admin/users" },
        { path: "users", component: () => import("../views/admin/Users.vue") },
        { path: "data", component: () => import("../views/admin/Data.vue") },
        { path: "stats", component: () => import("../views/admin/Stats.vue") },
        { path: "graph", component: () => import("../views/admin/Graph.vue") },
        { path: "models", component: () => import("../views/admin/Models.vue") },
        { path: "eval", component: () => import("../views/admin/Eval.vue") },
        { path: "predictions", component: () => import("../views/admin/PredictAdmin.vue") },
      ],
    },
  ],
});

router.beforeEach((to) => {
  const token = localStorage.getItem("token");
  const role = localStorage.getItem("role");
  if (to.meta.auth && !token) return "/login";
  if (to.meta.admin && role !== "ADMIN") return "/products";
  if ((to.path === "/login" || to.path === "/register") && token) {
    return role === "ADMIN" ? "/admin" : "/products";
  }
  return true;
});

export default router;
