<template>
  <el-card>
    <div class="toolbar">
      <el-input v-model="keyword" placeholder="用户名或昵称" style="width:220px" @keyup.enter="load" />
      <el-button type="primary" @click="load">查询</el-button>
      <el-button @click="openCreate">新增用户</el-button>
    </div>
    <el-table :data="items">
      <el-table-column prop="username" label="用户名" />
      <el-table-column prop="nickname" label="昵称" />
      <el-table-column label="角色" width="120">
        <template #default="{ row }">
          <el-tag :type="row.role === 'ADMIN' ? 'warning' : 'info'" effect="plain">{{ row.role === "ADMIN" ? "管理员" : "普通用户" }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'ENABLED' ? 'success' : 'info'">{{ row.status === "ENABLED" ? "启用" : "停用" }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="260">
        <template #default="{ row }">
          <el-button link @click="openEdit(row)">编辑</el-button>
          <el-button link @click="toggle(row)">{{ row.status === "ENABLED" ? "停用" : "启用" }}</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination class="pager" layout="total, prev, pager, next" :total="total" v-model:current-page="page" :page-size="10" @current-change="load" />
    <el-dialog v-model="visible" :title="editing ? '编辑用户' : '新增用户'" width="460px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="用户名"><el-input v-model="form.username" :disabled="editing" /></el-form-item>
        <el-form-item v-if="!editing" label="密码"><el-input v-model="form.password" /></el-form-item>
        <el-form-item label="昵称"><el-input v-model="form.nickname" /></el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role"><el-option label="普通用户" value="USER" /><el-option label="管理员" value="ADMIN" /></el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import http from "../../api/http";

const items = ref<any[]>([]);
const keyword = ref("");
const page = ref(1);
const total = ref(0);
const visible = ref(false);
const editing = ref(false);
const form = reactive<any>({ id: 0, username: "", password: "", nickname: "", role: "USER" });

async function load() {
  const data: any = await http.get("/admin/users", { params: { keyword: keyword.value, page: page.value, pageSize: 10 } });
  items.value = data.items;
  total.value = data.total;
}
function openCreate() {
  editing.value = false;
  Object.assign(form, { id: 0, username: "", password: "", nickname: "", role: "USER" });
  visible.value = true;
}
function openEdit(row: any) {
  editing.value = true;
  Object.assign(form, row);
  visible.value = true;
}
async function save() {
  if (editing.value) await http.put("/admin/users/" + form.id, { nickname: form.nickname, role: form.role });
  else await http.post("/admin/users", form);
  visible.value = false;
  ElMessage.success("已保存");
  await load();
}
async function toggle(row: any) {
  await http.put(`/admin/users/${row.id}/status`, { status: row.status === "ENABLED" ? "DISABLED" : "ENABLED" });
  await load();
}
async function remove(row: any) {
  const data: any = await http.delete("/admin/users/" + row.id);
  ElMessage.success(data?.disabled ? "已改为停用" : "已删除");
  await load();
}
onMounted(load);
</script>

<style scoped>
.toolbar { display: flex; gap: 8px; margin-bottom: 12px; }
.pager { margin-top: 12px; }
</style>
