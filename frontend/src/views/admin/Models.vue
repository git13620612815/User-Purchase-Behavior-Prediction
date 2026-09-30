<template>
  <div>
    <el-card class="block">
      <el-form :inline="true" :model="form">
        <el-form-item label="算法">
          <el-select v-model="form.algorithm" style="width:160px">
            <el-option label="HeteroSAGE" value="HETERO_SAGE" />
            <el-option label="GCN（仅对比）" value="GCN" />
            <el-option label="GAT（仅对比）" value="GAT" />
          </el-select>
        </el-form-item>
        <el-form-item label="学习率"><el-input-number v-model="form.learningRate" :step="0.001" :min="0.0001" :max="0.9" /></el-form-item>
        <el-form-item label="批大小"><el-input-number v-model="form.batchSize" :min="1" :max="10000" /></el-form-item>
        <el-form-item label="轮数"><el-input-number v-model="form.epochs" :min="1" :max="200" /></el-form-item>
        <el-button type="primary" :disabled="running" @click="train">开始训练</el-button>
        <el-button :disabled="running" @click="compare">对比三种算法</el-button>
      </el-form>
      <el-alert v-if="running" title="已有训练任务在执行，不能再次开始" type="info" :closable="false" />
      <pre class="log">{{ job?.logText }}</pre>
    </el-card>
    <el-card>
      <el-table :data="versions">
        <el-table-column prop="versionNo" label="版本" />
        <el-table-column prop="algorithm" label="算法" width="140" />
        <el-table-column prop="status" label="状态" width="120" />
        <el-table-column label="AUC" width="100"><template #default="{ row }">{{ row.metrics?.auc ?? "-" }}</template></el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button v-if="row.onlineAllowed && row.status !== 'ENABLED'" link type="primary" @click="enable(row)">启用</el-button>
            <el-button v-if="row.status === 'ENABLED'" link @click="disable(row)">停用</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import http from "../../api/http";

const form = reactive({ algorithm: "HETERO_SAGE", learningRate: 0.001, batchSize: 1024, epochs: 30 });
const job = ref<any>(null);
const versions = ref<any[]>([]);
const running = ref(false);
let timer: number | undefined;

async function refresh() {
  job.value = await http.get("/admin/train/current");
  running.value = job.value?.status === "RUNNING";
  versions.value = await http.get("/admin/models");
}
async function train() {
  await http.post("/admin/train", form);
  ElMessage.success("训练已开始");
  await refresh();
}
async function compare() {
  await http.post("/admin/models/compare", { learningRate: form.learningRate, batchSize: form.batchSize, epochs: form.epochs, algorithms: ["HETERO_SAGE", "GCN", "GAT"] });
  ElMessage.success("对比任务已开始");
  await refresh();
}
async function enable(row: any) {
  await http.put(`/admin/models/${row.id}/enable`);
  ElMessage.success("已启用");
  await refresh();
}
async function disable(row: any) {
  await http.put(`/admin/models/${row.id}/disable`);
  await refresh();
}
onMounted(() => {
  refresh();
  timer = window.setInterval(refresh, 3000);
});
onBeforeUnmount(() => window.clearInterval(timer));
</script>

<style scoped>
.block { margin-bottom: 12px; }
.log { white-space: pre-wrap; background: #111827; color: #e5e7eb; padding: 12px; min-height: 80px; max-height: 240px; overflow: auto; }
</style>
