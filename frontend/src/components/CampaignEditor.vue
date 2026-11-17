<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const campaignId = route.params.id

const streams = ref([])
const loading = ref(false)

const fetchStreams = async () => {
  loading.value = true
  try {
    const response = await axios.get(`/api/campaigns/${campaignId}/streams`)
    streams.value = response.data.streams
  } catch (error) {
    ElMessage.error('Ошибка при загрузке потоков')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const goBack = () => {
  router.push('/')
}

// Разделяем потоки на те, где есть офферы, и те, где их нет
const streamsWithOffers = computed(() => 
  streams.value.filter(s => s.offers && s.offers.length > 0)
)

const streamsWithoutOffers = computed(() => 
  streams.value.filter(s => !s.offers || s.offers.length === 0)
)

onMounted(() => {
  fetchStreams()
})
</script>

<template>
  <div class="container">
    <div class="header">
      <el-button @click="goBack" size="large">← Назад к списку</el-button>
      <h1>Редактор кампании #{{ campaignId }}</h1>
    </div>

    <div v-loading="loading" class="streams-container">
      
      <!-- 1. Сначала выводим потоки с офферами (с таблицами) -->
      <div v-for="stream in streamsWithOffers" :key="stream.id" class="stream-block">
        <div class="stream-name">
          {{ stream.name }} (ID: {{ stream.id }})
        </div>
        
        <el-table :data="stream.offers" style="width: 100%">
          <el-table-column label="offers" min-width="350">
            <template #default="scope">
              <div style="display: flex; flex-direction: column; gap: 4px;">
                <span style="font-weight: 600; color: #303133; font-size: 14px;">
                  ID: {{ scope.row.offer_id }}
                </span>
                <!-- Обрезаем на фронтенде только для отображения, но title содержит полное имя -->
                <span 
                  style="font-size: 13px; color: #606266; line-height: 1.4; cursor: help;" 
                  :title="scope.row.offer_name"
                >
                  {{ scope.row.offer_name.length > 70 ? scope.row.offer_name.slice(0, 70) + '...' : scope.row.offer_name }}
                </span>
              </div>
            </template>
          </el-table-column>
          
          <el-table-column label="share" width="100" align="center">
            <template #default="scope">
              {{ scope.row.share }}%
            </template>
          </el-table-column>
          
          <el-table-column label="stats" width="120" align="center">
            <template #default>
              <span style="color: #909399; font-size: 13px;">—</span>
            </template>
          </el-table-column>
          
          <el-table-column label="trends" width="120" align="center">
            <template #default>
              <span style="color: #909399; font-size: 13px;">—</span>
            </template>
          </el-table-column>
          
          <el-table-column label="actions" width="130" align="center">
            <template #default="scope">
              <el-button size="small" type="danger" @click="ElMessage.info('Удаление оффера (скоро)')">
                Удалить
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        
        <!-- Кнопка добавления оффера (заглушка на сейчас) -->
        <div class="stream-actions">
          <el-button type="primary" size="small" @click="ElMessage.info('Добавление оффера (скоро)')">
            + Добавить оффер
          </el-button>
        </div>
      </div>

      <!-- 2. Внизу выводим потоки без офферов (просто строка с названием) -->
      <div v-if="streamsWithoutOffers.length > 0" class="no-offers-section">
        <h3>Другие потоки (без офферов):</h3>
        <div v-for="stream in streamsWithoutOffers" :key="stream.id" class="simple-stream-row">
          <el-tag type="info">{{ stream.name }}</el-tag>
          <span class="stream-id">ID: {{ stream.id }}</span>
        </div>
      </div>

      <el-empty v-if="streams.length === 0 && !loading" description="Потоки не найдены" />
    </div>
  </div>
</template>

<style scoped>
.container {
  max-width: 1000px;
  margin: 40px auto;
  padding: 20px;
  font-family: Arial, sans-serif;
}

.header {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 30px;
}

h1 {
  margin: 0;
  color: #333;
}

.streams-container {
  margin-top: 20px;
}

.stream-block {
  margin-bottom: 30px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  overflow: hidden;
  background: #fff;
}

.stream-name {
  background-color: #f5f7fa;
  padding: 12px 16px;
  font-weight: 600;
  font-size: 16px;
  color: #303133;
  border-bottom: 1px solid #e4e7ed;
}

.stream-actions {
  padding: 12px 16px;
  background-color: #fafafa;
  border-top: 1px solid #e4e7ed;
  text-align: right;
}

.no-offers-section {
  margin-top: 40px;
  padding-top: 20px;
  border-top: 2px dashed #e4e7ed;
}

.no-offers-section h3 {
  margin-top: 0;
  color: #909399;
  font-size: 14px;
  font-weight: normal;
}

.simple-stream-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
}

.stream-id {
  color: #909399;
  font-size: 13px;
}
</style>