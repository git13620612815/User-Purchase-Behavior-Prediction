<template>
  <div ref="el" class="chart"></div>
</template>

<script setup lang="ts">
import * as echarts from "echarts";
import { onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = defineProps<{ option: Record<string, unknown> }>();
const el = ref<HTMLDivElement>();
let chart: echarts.ECharts | null = null;

onMounted(() => {
  chart = echarts.init(el.value!);
  chart.setOption(props.option);
  window.addEventListener("resize", resize);
});
watch(() => props.option, (value) => chart?.setOption(value, true), { deep: true });
onBeforeUnmount(() => {
  window.removeEventListener("resize", resize);
  chart?.dispose();
});
function resize() { chart?.resize(); }
</script>

<style scoped>
.chart { height: 320px; }
</style>
