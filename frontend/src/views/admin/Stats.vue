<template>
  <div>
    <el-card class="block">
      <div class="toolbar">
        <el-input v-model="userId" placeholder="用户 ID，空则看全站" style="width:220px" />
        <el-button type="primary" @click="loadUser">用户行为分析</el-button>
      </div>
      <el-descriptions v-if="userStat" :column="3" border>
        <el-descriptions-item label="活跃天数">{{ userStat.activeDays }}</el-descriptions-item>
        <el-descriptions-item label="购买频率">{{ userStat.purchaseFrequency }}</el-descriptions-item>
        <el-descriptions-item label="购买转化率">{{ userStat.purchaseConversion ?? userStat.purchaseConversionText }}</el-descriptions-item>
        <el-descriptions-item label="浏览">{{ userStat.counts.browse }}</el-descriptions-item>
        <el-descriptions-item label="收藏">{{ userStat.counts.favorite }}</el-descriptions-item>
        <el-descriptions-item label="加购 / 购买">{{ userStat.counts.cart }} / {{ userStat.counts.purchase }}</el-descriptions-item>
      </el-descriptions>
    </el-card>
    <div class="grid">
      <el-card><h3>用户活跃趋势</h3><ChartBox :option="activeOption" /></el-card>
      <el-card><h3>商品购买趋势</h3><ChartBox :option="purchaseOption" /></el-card>
      <el-card><h3>行为漏斗</h3><ChartBox :option="funnelOption" /></el-card>
      <el-card><h3>类目分布</h3><ChartBox :option="categoryOption" /></el-card>
      <el-card><h3>购买时间热力图</h3><ChartBox :option="heatOption" /></el-card>
      <el-card><h3>Top 商品</h3><ChartBox :option="topOption" /></el-card>
    </div>
    <el-card>
      <h3>商品分析</h3>
      <el-table :data="products">
        <el-table-column prop="name" label="商品" />
        <el-table-column prop="categoryName" label="类目" />
        <el-table-column prop="browseCount" label="浏览" />
        <el-table-column prop="favoriteCount" label="收藏" />
        <el-table-column prop="cartCount" label="加购" />
        <el-table-column prop="purchaseCount" label="购买" />
        <el-table-column prop="conversion" label="转化率" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import http from "../../api/http";
import ChartBox from "../../components/ChartBox.vue";

const userId = ref("");
const userStat = ref<any>(null);
const products = ref<any[]>([]);
const activeOption = ref<any>({});
const purchaseOption = ref<any>({});
const funnelOption = ref<any>({});
const categoryOption = ref<any>({});
const heatOption = ref<any>({});
const topOption = ref<any>({});

function line(name: string, xs: string[], ys: number[]) {
  return { tooltip: { trigger: "axis" }, xAxis: { type: "category", data: xs }, yAxis: { type: "value" }, series: [{ name, type: "line", data: ys }] };
}
async function loadUser() {
  const path = userId.value ? `/admin/stats/users/${userId.value}` : "/admin/stats/users";
  userStat.value = await http.get(path);
}
onMounted(async () => {
  const data: any = await http.get("/admin/stats/overview");
  activeOption.value = line("活跃用户", data.activeTrend.map((i: any) => i.date), data.activeTrend.map((i: any) => i.userCount));
  purchaseOption.value = line("购买次数", data.purchaseTrend.map((i: any) => i.date), data.purchaseTrend.map((i: any) => i.count));
  funnelOption.value = { tooltip: {}, xAxis: { type: "category", data: data.funnel.map((i: any) => i.label) }, yAxis: { type: "value" }, series: [{ type: "bar", data: data.funnel.map((i: any) => i.count) }] };
  categoryOption.value = { tooltip: { trigger: "item" }, series: [{ type: "pie", data: data.categoryDistribution.map((i: any) => ({ name: i.name, value: i.count })) }] };
  const hours = Array.from({ length: 24 }, (_, i) => i + "时");
  const days = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"];
  heatOption.value = {
    tooltip: {},
    xAxis: { type: "category", data: hours },
    yAxis: { type: "category", data: days },
    visualMap: { min: 0, max: Math.max(1, ...data.heatmap.map((i: any) => i.count)), calculable: true, orient: "horizontal", left: "center", bottom: 0 },
    series: [{ type: "heatmap", data: data.heatmap.map((i: any) => [i.hour, i.weekday, i.count]) }],
  };
  topOption.value = { tooltip: {}, xAxis: { type: "value" }, yAxis: { type: "category", data: data.topProducts.map((i: any) => i.name).reverse() }, series: [{ type: "bar", data: data.topProducts.map((i: any) => i.purchaseCount).reverse() }] };
  const productData: any = await http.get("/admin/stats/products", { params: { page: 1, pageSize: 10 } });
  products.value = productData.items;
  await loadUser();
});
</script>

<style scoped>
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.block, .grid { margin-bottom: 12px; }
.toolbar { display: flex; gap: 8px; margin-bottom: 12px; }
</style>
