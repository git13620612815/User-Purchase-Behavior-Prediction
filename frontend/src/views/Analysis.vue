<template>
  <div class="grid">
    <el-card>
      <h3>行为占比</h3>
      <ChartBox :option="pie" />
    </el-card>
    <el-card>
      <h3>购买类目</h3>
      <ChartBox :option="bar" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import http from "../api/http";
import ChartBox from "../components/ChartBox.vue";

const pie = ref<any>({});
const bar = ref<any>({});
const labels: Record<string, string> = { browse: "浏览", favorite: "收藏", cart: "加购", purchase: "购买" };

onMounted(async () => {
  const data: any = await http.get("/analysis/me");
  pie.value = {
    tooltip: { trigger: "item" },
    series: [{ type: "pie", data: Object.keys(labels).map((key) => ({ name: labels[key], value: data.counts[key] || 0 })) }],
  };
  bar.value = {
    tooltip: {},
    xAxis: { type: "category", data: data.categoryStats.map((item: any) => item.name) },
    yAxis: { type: "value" },
    series: [{ type: "bar", data: data.categoryStats.map((item: any) => item.count) }],
  };
});
</script>

<style scoped>
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
</style>
