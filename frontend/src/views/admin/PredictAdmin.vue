<template>
  <div>
    <el-card class="block">
      <div class="toolbar">
        <el-select v-model="userId" filterable placeholder="选择用户" style="width:220px">
          <el-option v-for="item in users" :key="item.id" :label="item.username" :value="item.id" />
        </el-select>
        <el-button type="primary" @click="viewUser">查看该用户</el-button>
        <el-input v-model="keyword" placeholder="按用户名批量" style="width:180px" />
        <el-button @click="batch">批量计算</el-button>
        <el-button @click="exportResult">导出最近批量结果</el-button>
      </div>
      <el-alert v-if="statusText" :title="statusText" type="warning" show-icon :closable="false" />
      <h3>最近操作</h3>
      <el-table :data="behaviors">
        <el-table-column prop="behaviorTime" label="时间" width="180" />
        <el-table-column prop="productName" label="商品" />
        <el-table-column prop="behaviorLabel" label="行为" width="100" />
      </el-table>
      <h3>购买可能性</h3>
      <el-table :data="items">
        <el-table-column prop="productName" label="商品" />
        <el-table-column prop="categoryName" label="类目" width="140" />
        <el-table-column prop="probability" label="购买概率" width="120" />
        <el-table-column prop="source" label="来源" width="140" />
        <el-table-column prop="reason" label="理由" />
      </el-table>
    </el-card>
    <el-card class="block">
      <h3>全部预测记录</h3>
      <el-table :data="records">
        <el-table-column prop="createdAt" label="时间" width="180" />
        <el-table-column prop="username" label="用户" width="120" />
        <el-table-column prop="sourceLabel" label="来源" width="140" />
        <el-table-column prop="statusText" label="说明" />
        <el-table-column prop="elapsedMs" label="耗时 ms" width="100" />
      </el-table>
      <el-pagination class="pager" layout="total, prev, pager, next" :total="total" v-model:current-page="page" :page-size="10" @current-change="loadRecords" />
    </el-card>
    <div class="grid" v-if="analysis">
      <el-card><h3>概率分布</h3><ChartBox :option="distOption" /></el-card>
      <el-card>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="预测次数">{{ analysis.predictionCount }}</el-descriptions-item>
          <el-descriptions-item label="模型成功次数">{{ analysis.successCount }}</el-descriptions-item>
          <el-descriptions-item label="成功率">{{ analysis.successRate }}</el-descriptions-item>
          <el-descriptions-item label="兜底次数">{{ analysis.fallbackCount }}</el-descriptions-item>
          <el-descriptions-item label="平均耗时 ms">{{ analysis.avgElapsedMs }}</el-descriptions-item>
          <el-descriptions-item label="高概率用户（≥0.7）">{{ analysis.highProbabilityUsers }}</el-descriptions-item>
        </el-descriptions>
        <h3>潜在购买商品</h3>
        <el-table :data="analysis.potentialProducts">
          <el-table-column prop="name" label="商品" />
          <el-table-column prop="count" label="出现次数" width="120" />
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import http from "../../api/http";
import ChartBox from "../../components/ChartBox.vue";

const users = ref<any[]>([]);
const userId = ref<number>();
const keyword = ref("");
const behaviors = ref<any[]>([]);
const items = ref<any[]>([]);
const statusText = ref("");
const records = ref<any[]>([]);
const total = ref(0);
const page = ref(1);
const analysis = ref<any>(null);
const distOption = ref<any>({});

async function loadRecords() {
  const data: any = await http.get("/admin/predictions", { params: { page: page.value, pageSize: 10 } });
  records.value = data.items;
  total.value = data.total;
}
async function loadAnalysis() {
  analysis.value = await http.get("/admin/predictions/analysis");
  distOption.value = {
    tooltip: {},
    xAxis: { type: "category", data: analysis.value.distribution.map((i: any) => `${i.start}-${i.end}`) },
    yAxis: { type: "value" },
    series: [{ type: "bar", data: analysis.value.distribution.map((i: any) => i.count) }],
  };
}
async function viewUser() {
  const data: any = await http.get("/admin/predictions/users/" + userId.value);
  behaviors.value = data.behaviors;
  items.value = data.prediction.items;
  statusText.value = data.prediction.statusText;
  await loadRecords();
  await loadAnalysis();
}
async function batch() {
  await http.post("/admin/predictions/batch", { keyword: keyword.value, userIds: userId.value ? [userId.value] : [] });
  await loadRecords();
  await loadAnalysis();
}
async function exportResult() {
  const blob: any = await http.get("/admin/predictions/export", { responseType: "blob" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "predictions.csv";
  link.click();
  URL.revokeObjectURL(url);
}
onMounted(async () => {
  const data: any = await http.get("/admin/users", { params: { page: 1, pageSize: 100 } });
  users.value = data.items;
  await loadRecords();
  await loadAnalysis();
});
</script>

<style scoped>
.block { margin-bottom: 12px; }
.toolbar { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.pager { margin-top: 12px; }
</style>
