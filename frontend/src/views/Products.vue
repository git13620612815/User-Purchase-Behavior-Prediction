<template>
  <div class="mall">
    <div class="search-bar">
      <div class="cats">
        <button type="button" :class="{ on: !categoryId }" @click="pickCategory()">全部</button>
        <button v-for="item in categories" :key="item.id" type="button" :class="{ on: categoryId === item.id }" @click="pickCategory(item.id)">
          {{ item.name }}
        </button>
      </div>
      <div class="search">
        <el-input v-model="keyword" placeholder="搜索商品名称或编号" clearable @keyup.enter="search" />
        <el-button class="search-btn" @click="search">搜索</el-button>
      </div>
    </div>
    <div class="grid">
      <article v-for="item in items" :key="item.id" class="card" @click="open(item.id)">
        <img class="cover" :src="productPhoto(item.skuCode)" :alt="item.name" />
        <h3>{{ item.name }}</h3>
        <p class="price"><small>¥</small>{{ formatPrice(item.price) }}</p>
        <p class="meta">{{ item.categoryName }} · {{ item.skuCode }}</p>
      </article>
    </div>
    <el-empty v-if="ready && !items.length" description="没有找到商品" />
    <el-pagination v-if="ready" class="pager" layout="total, prev, pager, next" :total="total" v-model:current-page="page" :page-size="pageSize" @current-change="load" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import http from "../api/http";
import { productPhoto } from "../utils/productPhoto";

const route = useRoute();
const router = useRouter();
const categories = ref<any[]>([]);
const items = ref<any[]>([]);
const categoryId = ref<number | undefined>(route.query.categoryId ? Number(route.query.categoryId) : undefined);
const keyword = ref(typeof route.query.keyword === "string" ? route.query.keyword : "");
const page = ref(readPage());
const pageSize = 12;
const total = ref(0);
const ready = ref(false);
function readPage() {
  const value = Number(route.query.page);
  return Number.isInteger(value) && value > 0 ? value : 1;
}
function formatPrice(value: number) {
  return Number(value || 0).toFixed(2);
}
function pickCategory(id?: number) {
  categoryId.value = id;
  search();
}
function open(id: number) {
  router.push("/products/" + id);
}
function search() {
  page.value = 1;
  return load();
}
async function load() {
  const query: Record<string, string> = {};
  if (page.value > 1) query.page = String(page.value);
  if (categoryId.value) query.categoryId = String(categoryId.value);
  const text = keyword.value.trim();
  if (text) query.keyword = text;
  const currentPage = typeof route.query.page === "string" ? route.query.page : "";
  const currentCategory = typeof route.query.categoryId === "string" ? route.query.categoryId : "";
  const currentKeyword = typeof route.query.keyword === "string" ? route.query.keyword : "";
  if (currentPage !== (query.page || "") || currentCategory !== (query.categoryId || "") || currentKeyword !== (query.keyword || "")) {
    await router.replace({ path: "/products", query });
  }
  const data: any = await http.get("/products", { params: { categoryId: categoryId.value, keyword: text, page: page.value, pageSize } });
  items.value = data.items;
  total.value = data.total;
  const pages = Math.max(1, Math.ceil(data.total / pageSize));
  if (page.value > pages) {
    page.value = pages;
    await load();
  }
}
onMounted(async () => {
  categories.value = await http.get("/categories");
  await load();
  ready.value = true;
});
</script>

<style scoped>
.mall { display: flex; flex-direction: column; gap: 16px; }
.search-bar { background: #fff; border-radius: 8px; padding: 16px; }
.cats { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
.cats button {
  border: none;
  background: #f5f5f5;
  color: #333;
  border-radius: 14px;
  padding: 6px 14px;
  cursor: pointer;
}
.cats button.on { background: #ff5000; color: #fff; }
.search { display: flex; max-width: 640px; }
.search :deep(.el-input__wrapper) { border-radius: 4px 0 0 4px; }
.search-btn { border-radius: 0 4px 4px 0; background: #ff5000; border-color: #ff5000; color: #fff; }
.search-btn:hover { background: #ff6a00; border-color: #ff6a00; color: #fff; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 12px; }
.card { background: #fff; border-radius: 8px; overflow: hidden; cursor: pointer; }
.card:hover { box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08); }
.cover { width: 100%; height: 180px; object-fit: contain; background: #f6f6f6; display: block; }
.card h3 {
  margin: 10px 12px 6px;
  height: 40px;
  line-height: 20px;
  font-size: 14px;
  font-weight: 400;
  color: #333;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.price { margin: 0 12px; color: #ff5000; font-size: 20px; font-weight: 700; }
.price small { font-size: 13px; margin-right: 2px; }
.meta { margin: 6px 12px 12px; color: #999; font-size: 12px; }
.pager { justify-content: flex-end; }
</style>
