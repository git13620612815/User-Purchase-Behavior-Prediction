<template>
  <div class="profile">
  <el-card>
    <h3>个人资料</h3>
    <el-form :model="form" label-width="80px" style="max-width:480px">
      <el-form-item label="用户名"><el-input v-model="form.username" disabled /></el-form-item>
      <el-form-item label="昵称"><el-input v-model="form.nickname" /></el-form-item>
      <el-form-item label="性别">
        <el-select v-model="form.gender"><el-option label="男" value="男" /><el-option label="女" value="女" /><el-option label="未知" value="未知" /></el-select>
      </el-form-item>
      <el-form-item label="年龄"><el-input-number v-model="form.age" :min="0" :max="120" /></el-form-item>
      <el-form-item label="手机"><el-input v-model="form.phone" /></el-form-item>
      <el-form-item label="邮箱"><el-input v-model="form.email" /></el-form-item>
      <el-button type="primary" @click="save">保存资料</el-button>
    </el-form>
  </el-card>
  <el-card>
    <h3>修改密码</h3>
    <el-form :model="password" label-width="80px" style="max-width:480px">
      <el-form-item label="原密码"><el-input v-model="password.oldPassword" type="password" show-password /></el-form-item>
      <el-form-item label="新密码"><el-input v-model="password.newPassword" type="password" show-password /></el-form-item>
      <el-button @click="changePassword">修改密码</el-button>
    </el-form>
  </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive } from "vue";
import { ElMessage } from "element-plus";
import http from "../api/http";

const form = reactive<any>({ username: "", nickname: "", gender: "未知", age: 0, phone: "", email: "" });
const password = reactive({ oldPassword: "", newPassword: "" });
onMounted(async () => Object.assign(form, await http.get("/users/me")));
async function save() {
  await http.put("/users/me", { nickname: form.nickname, gender: form.gender, age: form.age, phone: form.phone, email: form.email });
  ElMessage.success("已保存");
}
async function changePassword() {
  await http.put("/users/me/password", password);
  ElMessage.success("密码已修改");
  password.oldPassword = "";
  password.newPassword = "";
}
</script>

<style scoped>
.profile { display: grid; gap: 16px; max-width: 640px; }
h3 { margin: 0 0 16px; }
</style>
