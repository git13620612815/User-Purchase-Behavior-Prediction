<template>
  <el-card>
    <div class="counts">
      <el-tag v-for="item in countTags" :key="item.key">{{ item.label }} {{ counts[item.key] || 0 }}</el-tag>
    </div>
    <el-radio-group v-model="behaviorType" @change="load">
      <el-radio-button value="">全部</el-radio-button>
      <el-radio-button value="browse">浏览</el-radio-button>
      <el-radio-button value="favorite">收藏</el-radio-button>
      <el-radio-button value="cart">加购</el-radio-button>
      <el-radio-button value="purchase">购买</el-radio-button>
    </el-radio-group>
    <el-table :data="items" style="margin-top:12px">
      <el-table-column prop="behaviorTime" label="时间" width="180" />
      <el-table-column prop="productName" label="商品" />
      <el-table-column prop="skuCode" label="编号" width="120" />
      <el-table-column prop="behaviorLabel" label="行为" width="100" />
    </el-table>
    <el-pagination class="pager" layout="total, prev, pager, next" :total="total" v-model:current-page="page" :page-size="10" @current-change="load" />
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import http from "../api/http";

const items = ref<any[]>([]);
const counts = ref<Record<string, number>>({});
const behaviorType = ref("");
const page = ref(1);
const total = ref(0);
const countTags = [
  { key: "browse", label: "浏览" },
  { key: "favorite", label: "收藏" },
  { key: "cart", label: "加购" },
  { key: "purchase", label: "购买" },
];
async function load() {
  const data: any = await http.get("/behaviors/mine", { params: { behaviorType: behaviorType.value || undefined, page: page.value, pageSize: 10 } });
  items.value = data.items;
  counts.value = data.counts;
  total.value = data.total;
}
onMounted(load);
</script>

<style scoped>
.counts { display: flex; gap: 8px; margin-bottom: 12px; }
.pager { margin-top: 12px; }
</style>
