<template>
  <div class="wrap">
    <el-card class="card">
      <h2>注册</h2>
      <el-form :model="form" @submit.prevent="submit">
        <el-form-item label="用户名"><el-input v-model="form.username" placeholder="4-32 位字母或数字" /></el-form-item>
        <el-form-item label="密码"><el-input v-model="form.password" type="password" show-password placeholder="至少 8 位，含字母和数字" /></el-form-item>
        <el-form-item label="昵称"><el-input v-model="form.nickname" /></el-form-item>
        <el-button type="primary" native-type="submit" :loading="loading" style="width:100%">注册</el-button>
      </el-form>
      <div class="extra"><router-link to="/login">返回登录</router-link></div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import http from "../api/http";

const router = useRouter();
const loading = ref(false);
const form = reactive({ username: "", password: "", nickname: "" });
async function submit() {
  loading.value = true;
  try {
    await http.post("/auth/register", form);
    ElMessage.success("注册成功，请登录");
    router.push("/login");
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.wrap { min-height: 100vh; display: flex; align-items: center; justify-content: center; }
.card { width: 420px; }
.extra { margin-top: 12px; text-align: right; }
</style>
