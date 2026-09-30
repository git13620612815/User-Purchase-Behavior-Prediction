<template>
  <el-card>
    <div class="toolbar">
      <span>{{ createdAt }}</span>
      <el-tag>{{ sourceLabel }}</el-tag>
      <el-alert v-if="statusText" :title="statusText" type="warning" :closable="false" />
      <el-select v-model="categoryId" clearable placeholder="按类目筛选" style="width:180px" @change="load">
        <el-option v-for="item in categories" :key="item.id" :label="item.name" :value="item.id" />
      </el-select>
    </div>
    <el-table :data="items">
      <el-table-column prop="productName" label="商品" />
      <el-table-column prop="categoryName" label="类目" width="140" />
      <el-table-column prop="probability" label="购买概率" width="120" />
      <el-table-column prop="source" label="来源" width="120" />
      <el-table-column prop="reason" label="理由" />
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import http from "../api/http";

const route = useRoute();
const items = ref<any[]>([]);
const categories = ref<any[]>([]);
const categoryId = ref<number | undefined>();
const statusText = ref("");
const sourceLabel = ref("");
const createdAt = ref("");

async function load() {
  const data: any = await http.get("/predictions/" + route.params.id, { params: { categoryId: categoryId.value } });
  items.value = data.items;
  statusText.value = data.statusText;
  sourceLabel.value = data.sourceLabel;
  createdAt.value = data.createdAt;
}
onMounted(async () => {
  categories.value = await http.get("/categories");
  await load();
});
</script>

<style scoped>
.toolbar { display: flex; gap: 12px; align-items: center; margin-bottom: 12px; }
</style>
