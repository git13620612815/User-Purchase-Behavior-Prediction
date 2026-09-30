<template>
  <el-container class="shell">
    <el-aside width="232px" class="shell-aside">
      <div class="shell-brand">
        <span class="shell-mark">购</span>
        <div>
          <strong>购买行为预测</strong>
          <small>普通用户</small>
        </div>
      </div>
      <el-menu :router="true" :default-active="active">
        <el-menu-item-group title="选购">
          <el-menu-item index="/products">商品</el-menu-item>
        </el-menu-item-group>
        <el-menu-item-group title="记录">
          <el-menu-item index="/behaviors">我的行为</el-menu-item>
        </el-menu-item-group>
        <el-menu-item-group title="预测">
          <el-menu-item index="/predictions">预测记录</el-menu-item>
          <el-menu-item index="/analysis">个人分析</el-menu-item>
        </el-menu-item-group>
        <el-menu-item-group title="账户">
          <el-menu-item index="/profile">个人中心</el-menu-item>
        </el-menu-item-group>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="shell-header">
        <h1>{{ title }}</h1>
        <div class="shell-user">
          <span>{{ name }}</span>
          <el-button link type="danger" @click="logout">退出</el-button>
        </div>
      </el-header>
      <el-main class="shell-main"><router-view /></el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import http from "../api/http";

const route = useRoute();
const router = useRouter();
const name = localStorage.getItem("lastUsername") || "用户";
const titles: Record<string, string> = {
  "/products": "商品",
  "/behaviors": "我的行为",
  "/predictions": "预测记录",
  "/analysis": "个人分析",
  "/profile": "个人中心",
};
const active = computed(() => {
  if (route.path.startsWith("/products")) return "/products";
  if (route.path.startsWith("/predictions")) return "/predictions";
  return route.path;
});
const title = computed(() => (route.path.startsWith("/products/") ? "商品详情" : route.path.startsWith("/predictions/") ? "预测详情" : titles[active.value] || "购买行为预测"));

async function logout() {
  try { await http.post("/auth/logout"); } catch { /* 已失效也退出 */ }
  localStorage.removeItem("token");
  localStorage.removeItem("role");
  router.push("/login");
}
</script>
