<template>
  <el-card>
    <div class="toolbar">
      <el-button type="primary" :loading="loading" @click="run">计算购买可能性</el-button>
      <el-select v-model="categoryId" clearable placeholder="按类目筛选" style="width:180px">
        <el-option v-for="item in categories" :key="item.categoryId" :label="item.categoryName" :value="item.categoryId" />
      </el-select>
      <el-alert v-if="statusText" :title="statusText" type="warning" :closable="false" show-icon />
    </div>
    <el-table :data="shown">
      <el-table-column prop="rankNo" label="排名" width="70" />
      <el-table-column prop="productName" label="商品" />
      <el-table-column prop="categoryName" label="类目" width="140" />
      <el-table-column prop="probability" label="购买概率" width="120" />
      <el-table-column prop="source" label="来源" width="120" />
      <el-table-column prop="reason" label="理由" />
    </el-table>
    <p class="hint">结果在计算完成时已保存，可在预测记录中查看。</p>
  </el-card>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import http from "../api/http";

const loading = ref(false);
const items = ref<any[]>([]);
const statusText = ref("");
const categoryId = ref<number | undefined>();
const categories = computed(() => {
  const map = new Map<number, string>();
  items.value.forEach((item) => map.set(item.categoryId, item.categoryName));
  return [...map.entries()].map(([id, name]) => ({ categoryId: id, categoryName: name }));
});
const shown = computed(() => items.value.filter((item) => !categoryId.value || item.categoryId === categoryId.value));

async function run() {
  loading.value = true;
  try {
    const data: any = await http.post("/predictions");
    items.value = data.items;
    statusText.value = data.statusText;
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.toolbar { display: flex; gap: 12px; align-items: center; margin-bottom: 12px; }
.hint { color: #6b7280; }
</style>
