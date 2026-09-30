<template>
  <el-tabs v-model="tab">
    <el-tab-pane label="导入" name="import">
      <el-card>
        <p>Excel 请先另存为 UTF-8 CSV。导入用户的初始密码为 Import12345。样例文件在 data/samples。</p>
        <div class="toolbar">
          <el-select v-model="targetTable" style="width:140px">
            <el-option label="用户" value="user" />
            <el-option label="商品" value="product" />
            <el-option label="行为" value="behavior" />
          </el-select>
          <input type="file" accept=".csv" @change="onFile" />
          <el-button type="primary" :disabled="!batchId" @click="commit">确认导入</el-button>
        </div>
        <div class="toolbar">
          <el-input v-model="keyword" placeholder="预览搜索" style="width:220px" @keyup.enter="loadPreview" />
          <el-button @click="loadPreview">搜索</el-button>
        </div>
        <el-table :data="rows">
          <el-table-column v-for="col in columns" :key="col" :prop="col" :label="col" />
        </el-table>
        <el-pagination class="pager" layout="total, prev, pager, next" :total="previewTotal" v-model:current-page="page" :page-size="10" @current-change="loadPreview" />
      </el-card>
    </el-tab-pane>
    <el-tab-pane label="商品" name="product">
      <el-card>
        <div class="toolbar">
          <el-input v-model="productKeyword" placeholder="名称或编号" style="width:220px" @keyup.enter="loadProducts" />
          <el-button type="primary" @click="loadProducts">查询</el-button>
        </div>
        <p class="hint">保存商品或导入新商品后，会用当前数据重新训练 HeteroSAGE。训练完成后到「模型训练」页启用新版本。</p>
        <el-table :data="products">
          <el-table-column prop="skuCode" label="编号" width="120" />
          <el-table-column prop="name" label="名称" />
          <el-table-column prop="categoryName" label="类目" />
          <el-table-column prop="price" label="价格" width="100" />
          <el-table-column prop="status" label="状态" width="90" />
          <el-table-column label="操作" width="90">
            <template #default="{ row }"><el-button link type="primary" @click="openProduct(row)">编辑</el-button></template>
          </el-table-column>
        </el-table>
      </el-card>
      <el-dialog v-model="productVisible" title="编辑商品" width="420px">
        <el-form label-width="72px" :model="productForm">
          <el-form-item label="编号"><el-input v-model="productForm.skuCode" /></el-form-item>
          <el-form-item label="名称"><el-input v-model="productForm.name" /></el-form-item>
          <el-form-item label="类目"><el-input v-model="productForm.categoryName" /></el-form-item>
          <el-form-item label="价格"><el-input-number v-model="productForm.price" :min="0" :precision="2" /></el-form-item>
          <el-form-item label="状态">
            <el-select v-model="productForm.status" style="width:100%">
              <el-option label="上架" value="ON" />
              <el-option label="下架" value="OFF" />
            </el-select>
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="productVisible = false">取消</el-button>
          <el-button type="primary" :loading="savingProduct" @click="saveProduct">保存并重新训练</el-button>
        </template>
      </el-dialog>
    </el-tab-pane>
    <el-tab-pane label="行为" name="behavior">
      <el-card>
        <div class="toolbar">
          <el-input v-model="behaviorKeyword" placeholder="用户、商品名或编号" style="width:240px" />
          <el-select v-model="behaviorType" clearable placeholder="行为" style="width:120px">
            <el-option label="浏览" value="browse" /><el-option label="收藏" value="favorite" /><el-option label="加购" value="cart" /><el-option label="购买" value="purchase" />
          </el-select>
          <el-button type="primary" @click="loadBehaviors">查询</el-button>
          <el-button @click="exportBehaviors">导出行为</el-button>
          <el-button type="warning" @click="clean">执行数据清洗</el-button>
        </div>
        <el-table :data="behaviors">
          <el-table-column prop="behaviorTime" label="时间" width="180" />
          <el-table-column prop="username" label="用户" width="120" />
          <el-table-column prop="productName" label="商品" />
          <el-table-column prop="behaviorLabel" label="行为" width="90" />
          <el-table-column label="操作" width="90">
            <template #default="{ row }"><el-button link type="danger" @click="removeBehavior(row)">删除</el-button></template>
          </el-table-column>
        </el-table>
        <el-pagination class="pager" layout="total, prev, pager, next" :total="behaviorTotal" v-model:current-page="behaviorPage" :page-size="10" @current-change="loadBehaviors" />
      </el-card>
    </el-tab-pane>
  </el-tabs>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import http from "../../api/http";

const tab = ref("import");
const targetTable = ref("behavior");
const batchId = ref<number | null>(null);
const columns = ref<string[]>([]);
const rows = ref<any[]>([]);
const keyword = ref("");
const page = ref(1);
const previewTotal = ref(0);
const products = ref<any[]>([]);
const productKeyword = ref("");
const productVisible = ref(false);
const savingProduct = ref(false);
const productForm = reactive({ id: 0, skuCode: "", name: "", categoryName: "", price: 0, status: "ON" });
const behaviors = ref<any[]>([]);
const behaviorKeyword = ref("");
const behaviorType = ref("");
const behaviorPage = ref(1);
const behaviorTotal = ref(0);

async function onFile(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!file) return;
  const body = new FormData();
  body.append("file", file);
  body.append("targetTable", targetTable.value);
  const data: any = await http.post("/admin/imports/preview", body);
  batchId.value = data.batchId;
  columns.value = data.columns;
  rows.value = data.rows;
  previewTotal.value = data.total;
  page.value = 1;
}
async function loadPreview() {
  if (!batchId.value) return;
  const data: any = await http.get(`/admin/imports/${batchId.value}/rows`, { params: { page: page.value, pageSize: 10, keyword: keyword.value } });
  columns.value = data.columns;
  rows.value = data.rows;
  previewTotal.value = data.total;
}
async function commit() {
  const data: any = await http.post(`/admin/imports/${batchId.value}/commit`);
  ElMessage.success(`成功 ${data.success}，拒绝 ${data.rejected}，重复 ${data.duplicate}${trainText(data.train)}`);
  if (targetTable.value === "product") await loadProducts();
}
function trainText(train: any) {
  if (!train) return "";
  if (train.started) return "，已开始重新训练";
  return train.message ? `，${train.message}` : "";
}
function openProduct(row: any) {
  productForm.id = row.id;
  productForm.skuCode = row.skuCode;
  productForm.name = row.name;
  productForm.categoryName = row.categoryName;
  productForm.price = row.price;
  productForm.status = row.status || "ON";
  productVisible.value = true;
}
async function saveProduct() {
  savingProduct.value = true;
  try {
    const data: any = await http.put(`/admin/products/${productForm.id}`, {
      skuCode: productForm.skuCode,
      name: productForm.name,
      categoryName: productForm.categoryName,
      price: productForm.price,
      status: productForm.status,
    });
    productVisible.value = false;
    ElMessage.success(`商品已保存${trainText(data.train)}`);
    await loadProducts();
  } finally {
    savingProduct.value = false;
  }
}
watch(tab, (name) => {
  if (name === "product") loadProducts();
});
async function loadProducts() {
  const data: any = await http.get("/admin/products", { params: { keyword: productKeyword.value, page: 1, pageSize: 20 } });
  products.value = data.items;
}
async function loadBehaviors() {
  const data: any = await http.get("/admin/behaviors", { params: { keyword: behaviorKeyword.value, behaviorType: behaviorType.value || undefined, page: behaviorPage.value, pageSize: 10 } });
  behaviors.value = data.items;
  behaviorTotal.value = data.total;
}
async function removeBehavior(row: any) {
  await http.delete("/admin/behaviors/" + row.id);
  await loadBehaviors();
}
async function clean() {
  const data: any = await http.post("/admin/data/clean");
  ElMessage.success(`删除非法 ${data.deletedIllegal} 条，重复 ${data.deletedDuplicate} 条`);
}
async function exportBehaviors() {
  const blob: any = await http.get("/admin/behaviors/export", { responseType: "blob" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "behaviors.csv";
  link.click();
  URL.revokeObjectURL(url);
}
</script>

<style scoped>
.toolbar { display: flex; gap: 8px; align-items: center; margin-bottom: 12px; flex-wrap: wrap; }
.hint { margin: 0 0 12px; color: #6b7c7e; }
.pager { margin-top: 12px; }
</style>
