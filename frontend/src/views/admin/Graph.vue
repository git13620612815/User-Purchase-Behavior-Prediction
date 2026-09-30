<template>
  <div v-if="data">
    <el-row :gutter="12">
      <el-col :span="8"><el-card><div class="num">{{ data.nodes.user }}</div><div>用户节点</div></el-card></el-col>
      <el-col :span="8"><el-card><div class="num">{{ data.nodes.product }}</div><div>商品节点</div></el-card></el-col>
      <el-col :span="8"><el-card><div class="num">{{ data.nodes.category }}</div><div>类目节点</div></el-card></el-col>
    </el-row>
    <el-card class="block">
      <h3>用户到商品的边</h3>
      <p>同一用户对同一商品只保留一条边，权重取最强行为。当前 {{ data.edges.userProduct }} 条。商品到类目 {{ data.edges.productCategory }} 条。</p>
      <el-table :data="data.weightRules">
        <el-table-column prop="label" label="行为" />
        <el-table-column prop="weight" label="权重" />
        <el-table-column prop="edgeCount" label="作为最强行为的边数" />
      </el-table>
      <el-table :data="data.behaviorEdges.items" style="margin-top:12px">
        <el-table-column prop="username" label="用户" width="120" />
        <el-table-column prop="productName" label="商品" />
        <el-table-column prop="categoryName" label="类目" width="120" />
        <el-table-column prop="behaviorLabel" label="最强行为" width="100" />
        <el-table-column prop="weight" label="权重" width="80" />
        <el-table-column prop="behaviorTime" label="时间" width="180" />
      </el-table>
      <el-pagination class="pager" layout="total, prev, pager, next" :total="data.behaviorEdges.total" v-model:current-page="page" :page-size="10" @current-change="load" />
    </el-card>
    <el-card class="block">
      <h3>商品到类目的边</h3>
      <el-table :data="data.categoryEdges">
        <el-table-column prop="skuCode" label="编号" width="120" />
        <el-table-column prop="productName" label="商品" />
        <el-table-column prop="categoryName" label="类目" />
      </el-table>
    </el-card>
    <el-card class="block">
      <h3>节点特征</h3>
      <p>{{ data.features.note }}</p>
      <el-descriptions :column="1" border>
        <el-descriptions-item label="用户">{{ data.features.user.join("、") }}</el-descriptions-item>
        <el-descriptions-item label="商品">{{ data.features.product.join("、") }}</el-descriptions-item>
        <el-descriptions-item label="类目">{{ data.features.category.join("、") }}</el-descriptions-item>
      </el-descriptions>
      <template v-if="data.scaler">
        <p>标准化参数来自 {{ data.scaler.versionNo }}（{{ data.scaler.status }}），年龄中位数 {{ data.scaler.ageMedian }}。</p>
        <el-table :data="scalerRows">
          <el-table-column prop="name" label="特征组" width="120" />
          <el-table-column prop="mean" label="训练集均值" />
          <el-table-column prop="std" label="训练集标准差" />
        </el-table>
      </template>
      <el-alert v-else title="还没有训练过的 HeteroSAGE，标准化参数会在训练完成后显示" type="info" :closable="false" />
    </el-card>
    <el-card v-if="data.split">
      <h3>按时间切分</h3>
      <p>行为按时间排序。要预测的购买不会提前进入图。</p>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="训练图历史">{{ data.split.historyCount }} 条，截至 {{ data.split.historyEnd }}</el-descriptions-item>
        <el-descriptions-item label="训练标签">{{ data.split.trainLabelCount }} 条，截至 {{ data.split.trainLabelEnd }}</el-descriptions-item>
        <el-descriptions-item label="验证集">{{ data.split.valCount }} 条，截至 {{ data.split.valEnd }}</el-descriptions-item>
        <el-descriptions-item label="测试集">{{ data.split.testCount }} 条，从 {{ data.split.testStart }} 起</el-descriptions-item>
      </el-descriptions>
    </el-card>
    <el-alert v-else title="有效行为不足，还不能按时间切分" type="warning" :closable="false" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import http from "../../api/http";

const data = ref<any>(null);
const page = ref(1);
const scalerRows = computed(() => {
  if (!data.value?.scaler) return [];
  return [
    { name: "用户", mean: data.value.scaler.userMean.join(", "), std: data.value.scaler.userStd.join(", ") },
    { name: "商品", mean: data.value.scaler.productMean.join(", "), std: data.value.scaler.productStd.join(", ") },
  ];
});
async function load() {
  data.value = await http.get("/admin/graph/summary", { params: { page: page.value, pageSize: 10 } });
}
onMounted(load);
</script>

<style scoped>
.num { font-size: 28px; font-weight: 700; }
.block { margin-top: 12px; }
.pager { margin-top: 12px; }
</style>
