<template>
  <el-container class="shell">
    <el-aside width="232px" class="shell-aside">
      <div class="shell-brand">
        <span class="shell-mark">管</span>
        <div>
          <strong>管理后台</strong>
          <small>管理员</small>
        </div>
      </div>
      <el-menu :router="true" :default-active="route.path">
        <el-menu-item-group title="账号">
          <el-menu-item index="/admin/users">用户管理</el-menu-item>
        </el-menu-item-group>
        <el-menu-item-group title="数据">
          <el-menu-item index="/admin/data">数据管理</el-menu-item>
          <el-menu-item index="/admin/stats">行为分析</el-menu-item>
          <el-menu-item index="/admin/graph">图数据</el-menu-item>
        </el-menu-item-group>
        <el-menu-item-group title="模型">
          <el-menu-item index="/admin/models">模型训练</el-menu-item>
          <el-menu-item index="/admin/eval">模型评估</el-menu-item>
        </el-menu-item-group>
        <el-menu-item-group title="预测">
          <el-menu-item index="/admin/predictions">购买可能性</el-menu-item>
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
const name = localStorage.getItem("lastUsername") || "管理员";
const titles: Record<string, string> = {
  "/admin/users": "用户管理",
  "/admin/data": "数据管理",
  "/admin/stats": "行为分析",
  "/admin/graph": "图数据",
  "/admin/models": "模型训练",
  "/admin/eval": "模型评估",
  "/admin/predictions": "购买可能性",
};
const title = computed(() => titles[route.path] || "管理后台");

async function logout() {
  try { await http.post("/auth/logout"); } catch { /* 忽略 */ }
  localStorage.removeItem("token");
  localStorage.removeItem("role");
  router.push("/login");
}
</script>
