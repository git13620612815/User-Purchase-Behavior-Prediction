<template>
  <div>
    <el-card class="block">
      <el-select v-model="versionId" placeholder="选择版本" style="width:360px" @change="loadCurves">
        <el-option v-for="item in versions" :key="item.id" :label="item.versionNo + ' / ' + item.algorithm" :value="item.id" />
      </el-select>
      <el-descriptions v-if="metrics" :column="4" border style="margin-top:12px">
        <el-descriptions-item label="AUC">{{ metrics.auc }}</el-descriptions-item>
        <el-descriptions-item label="Precision@10">{{ metrics.precisionAt10 }}</el-descriptions-item>
        <el-descriptions-item label="Recall@10">{{ metrics.recallAt10 }}</el-descriptions-item>
        <el-descriptions-item label="F1">{{ metrics.f1 }}</el-descriptions-item>
      </el-descriptions>
    </el-card>
    <div class="grid">
      <el-card><h3>训练损失</h3><ChartBox :option="lossOption" /></el-card>
      <el-card><h3>ROC</h3><ChartBox :option="rocOption" /></el-card>
      <el-card class="wide"><h3>版本指标对比</h3><ChartBox :option="barOption" /></el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import http from "../../api/http";
import ChartBox from "../../components/ChartBox.vue";

const versions = ref<any[]>([]);
const versionId = ref<number>();
const metrics = ref<any>(null);
const lossOption = ref<any>({});
const rocOption = ref<any>({});
const barOption = ref<any>({});

async function loadCurves() {
  if (!versionId.value) return;
  const data: any = await http.get(`/admin/models/${versionId.value}/curves`);
  metrics.value = data.metrics;
  lossOption.value = {
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: data.loss.map((i: any) => i.epoch) },
    yAxis: { type: "value" },
    series: [{ type: "line", data: data.loss.map((i: any) => i.trainLoss) }],
  };
  rocOption.value = {
    tooltip: {},
    xAxis: { type: "value", name: "FPR" },
    yAxis: { type: "value", name: "TPR" },
    series: [{ type: "line", data: data.roc.map((i: any) => [i.fpr, i.tpr]) }],
  };
}
onMounted(async () => {
  versions.value = await http.get("/admin/models");
  const names = versions.value.map((item) => item.versionNo);
  barOption.value = {
    tooltip: { trigger: "axis" },
    legend: { data: ["AUC", "Precision@10", "Recall@10", "F1"] },
    xAxis: { type: "category", data: names },
    yAxis: { type: "value", max: 1 },
    series: ["auc", "precisionAt10", "recallAt10", "f1"].map((key, index) => ({
      name: ["AUC", "Precision@10", "Recall@10", "F1"][index],
      type: "bar",
      data: versions.value.map((item) => item.metrics?.[key] ?? 0),
    })),
  };
  if (versions.value.length) {
    versionId.value = versions.value[0].id;
    await loadCurves();
  }
});
</script>

<style scoped>
.block { margin-bottom: 12px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.wide { grid-column: 1 / -1; }
</style>
