<template>
  <el-card>
    <el-table :data="items">
      <el-table-column prop="createdAt" label="时间" width="180" />
      <el-table-column prop="sourceLabel" label="来源" width="140" />
      <el-table-column prop="statusText" label="说明" />
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button link type="primary" @click="$router.push('/predictions/' + row.predictionId)">详情</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination class="pager" layout="total, prev, pager, next" :total="total" v-model:current-page="page" :page-size="10" @current-change="load" />
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import http from "../api/http";

const items = ref<any[]>([]);
const total = ref(0);
const page = ref(1);
async function load() {
  const data: any = await http.get("/predictions", { params: { page: page.value, pageSize: 10 } });
  items.value = data.items;
  total.value = data.total;
}
onMounted(load);
</script>

<style scoped>
.pager { margin-top: 12px; }
</style>
