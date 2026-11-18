<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'

const route = useRoute()
const router = useRouter()
const campaignId = route.params.id

// Состояние
const streams = ref([])         // Редактируемое состояние (в памяти)
const loadedStreams = ref([])   // Эталон: то, что синхронизировано с Keitaro/БД
const allOffers = ref([])       // Все офферы для автокомплита
const loading = ref(false)
const syncing = ref(false)

// Для автокомплита
const selectedOffer = ref(null)
const searchQuery = ref('')

// Dirty flag — есть ли изменения, не отправленные в Keitaro
const isDirty = computed(() => {
  const normalize = (streamsArr) => {
    return streamsArr.map(stream => ({
      id: stream.id,
      offers: (stream.offers || [])
        .map(o => ({
          offer_id: o.offer_id,
          share: o.share,
          state: o.state,
          deleted: o.deleted || false,
          pinned: o.pinned || false
        }))
        .sort((a, b) => a.offer_id - b.offer_id)
    })).sort((a, b) => a.id - b.id)
  }

  return JSON.stringify(normalize(streams.value)) !== JSON.stringify(normalize(loadedStreams.value))
})

// Загрузка данных с бэкенда
const fetchStreams = async () => {
  loading.value = true
  try {
    const [streamsRes, offersRes] = await Promise.all([
      axios.get(`/api/campaigns/${campaignId}/streams`),
      axios.get('/api/offers')
    ])

    streams.value = streamsRes.data.streams
    loadedStreams.value = JSON.parse(JSON.stringify(streamsRes.data.streams))
    allOffers.value = offersRes.data.offers
  } catch (error) {
    ElMessage.error('Ошибка при загрузке данных')
    console.error(error)
  } finally {
    loading.value = false
  }
}

// Сохранение состояния всех потоков в БД (вызывается только при синхронизации)
const saveAllToDb = async () => {
  for (const stream of streams.value) {
    await axios.put(`/api/streams/${stream.id}`, {
      campaign_id: parseInt(campaignId),
      offers: stream.offers.map(o => ({
        offer_id: o.offer_id,
        offer_name: o.offer_name || '',
        share: o.share,
        state: o.state,
        deleted: o.deleted || false,
        pinned: o.pinned || false
      }))
    })
  }
}

// Потоки с офферами (редактируемые)
const streamsWithOffers = computed(() =>
  streams.value.filter(s => s.offers && s.offers.length > 0)
)

// Потоки без офферов (только информация)
const streamsWithoutOffers = computed(() =>
  streams.value.filter(s => !s.offers || s.offers.length === 0)
)

// Автокомплит
const querySearch = (queryString, cb) => {
  const results = queryString
    ? allOffers.value.filter(offer =>
        offer.name.toLowerCase().includes(queryString.toLowerCase())
      )
    : allOffers.value
  cb(results)
}

// Обработка выбора оффера из автокомплита
const handleOfferSelect = (item) => {
  selectedOffer.value = item
  searchQuery.value = item.name
}

// Пересчёт share пропорционально (с учётом pinned и deleted)
const recalculateShares = (offers) => {
  const activeOffers = offers.filter(o => !o.deleted)

  if (activeOffers.length === 0) {
    offers.forEach(o => o.share = 0)
    return
  }

  const pinnedOffers = activeOffers.filter(o => o.pinned)
  const unpinnedOffers = activeOffers.filter(o => !o.pinned)

  const pinnedSum = pinnedOffers.reduce((sum, o) => sum + (o.share || 0), 0)

  // Если все зафиксированы — ничего не пересчитываем
  if (unpinnedOffers.length === 0) {
    offers.filter(o => o.deleted).forEach(o => o.share = 0)
    return
  }

  const remaining = Math.max(0, 100 - pinnedSum)
  const equalShare = Math.floor(remaining / unpinnedOffers.length)
  const remainder = remaining - (equalShare * unpinnedOffers.length)

  unpinnedOffers.forEach((offer, index) => {
    offer.share = equalShare + (index === unpinnedOffers.length - 1 ? remainder : 0)
  })

  // Удалённые офферы всегда с share = 0
  offers.filter(o => o.deleted).forEach(o => o.share = 0)
}

// Добавление оффера (только локально)
const addOffer = (streamId) => {
  if (!selectedOffer.value) {
    ElMessage.warning('Выберите оффер из списка')
    return
  }

  const stream = streams.value.find(s => s.id === streamId)
  if (!stream) return

  const existingOffer = stream.offers.find(o => o.offer_id === selectedOffer.value.id)
  if (existingOffer) {
    if (existingOffer.deleted) {
      existingOffer.deleted = false
      recalculateShares(stream.offers)
      ElMessage.success('Оффер восстановлен')
    } else {
      ElMessage.warning('Этот оффер уже добавлен в поток')
    }
    selectedOffer.value = null
    searchQuery.value = ''
    return
  }

  stream.offers.push({
    offer_id: selectedOffer.value.id,
    offer_name: selectedOffer.value.name,
    share: 0,
    state: 'active',
    deleted: false,
    pinned: false
  })

  recalculateShares(stream.offers)

  selectedOffer.value = null
  searchQuery.value = ''
}

// Удаление оффера (soft delete, только локально)
const removeOffer = (streamId, offerId) => {
  const stream = streams.value.find(s => s.id === streamId)
  if (!stream) return

  const offer = stream.offers.find(o => o.offer_id === offerId)
  if (!offer) return

  offer.deleted = true
  offer.share = 0

  recalculateShares(stream.offers)
}

// Восстановление удалённого оффера (только локально)
const restoreOffer = (streamId, offerId) => {
  const stream = streams.value.find(s => s.id === streamId)
  if (!stream) return

  const offer = stream.offers.find(o => o.offer_id === offerId)
  if (!offer) return

  offer.deleted = false
  recalculateShares(stream.offers)
}

// Фиксация/отмена фиксации веса (только локально)
const togglePin = (streamId, offerId) => {
  const stream = streams.value.find(s => s.id === streamId)
  if (!stream) return

  const offer = stream.offers.find(o => o.offer_id === offerId)
  if (!offer) return

  offer.pinned = !offer.pinned

  if (!offer.pinned) {
    recalculateShares(stream.offers)
  }
}

// Синхронизация с Keitaro: сначала БД, потом Keitaro
const syncToKeitaro = async () => {
  if (!isDirty.value) return

  syncing.value = true
  try {
    // 1. Фиксируем состояние в БД
    await saveAllToDb()

    // 2. Отправляем активные офферы в Keitaro
    for (const stream of streams.value) {
      await axios.post(`/api/streams/${stream.id}/sync`)
    }

    // 3. Обновляем эталон — таблица становится белой,
    //    удалённые офферы остаются в списке бледными
    loadedStreams.value = JSON.parse(JSON.stringify(streams.value))
    ElMessage.success('Изменения синхронизированы с Keitaro')
  } catch (error) {
    ElMessage.error('Ошибка синхронизации с Keitaro')
    console.error(error)
  } finally {
    syncing.value = false
  }
}

// Отмена изменений — откат к эталону (в БД ничего не писалось)
const cancelChanges = async () => {
  try {
    await ElMessageBox.confirm(
      'Все несохранённые изменения будут потеряны. Продолжить?',
      'Отмена изменений',
      {
        confirmButtonText: 'Да, отменить',
        cancelButtonText: 'Нет',
        type: 'warning'
      }
    )
    streams.value = JSON.parse(JSON.stringify(loadedStreams.value))
    ElMessage.success('Изменения отменены')
  } catch {
    // Пользователь нажал "Нет"
  }
}

// Обновление из Keitaro
const refreshFromKeitaro = async () => {
  // Защита от потери локальных изменений
  if (isDirty.value) {
    try {
      await ElMessageBox.confirm(
        'Есть несохранённые изменения. При обновлении из Keitaro они будут потеряны. Продолжить?',
        'Обновление данных',
        {
          confirmButtonText: 'Обновить',
          cancelButtonText: 'Отмена',
          type: 'warning'
        }
      )
    } catch {
      return
    }
  }

  loading.value = true
  try {
    for (const stream of streams.value) {
      await axios.post(`/api/streams/${stream.id}/refresh?campaign_id=${campaignId}`)
    }

    await fetchStreams()
    ElMessage.success('Данные обновлены из Keitaro')
  } catch (error) {
    ElMessage.error('Ошибка обновления из Keitaro')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const goBack = () => {
  router.push('/')
}

onMounted(() => {
  fetchStreams()
})
</script>

<template>
  <div class="container">
    <div class="header">
      <el-button @click="goBack" size="large">← Назад к списку</el-button>
      <h1>Редактор кампании #{{ campaignId }}</h1>
      <el-button @click="refreshFromKeitaro" :loading="loading" size="large">
        🔄 Обновить из Keitaro
      </el-button>
    </div>

    <!-- Баннер несохранённых изменений -->
    <div v-if="isDirty" class="dirty-banner">
      <span>⚠️ Есть изменения, не отправленные в Keitaro</span>
      <div class="banner-actions">
        <el-button type="success" @click="syncToKeitaro" :loading="syncing">
          💾 Сохранить в Keitaro
        </el-button>
        <el-button @click="cancelChanges" :disabled="syncing">
          ↶ Отменить изменения
        </el-button>
      </div>
    </div>

    <div v-loading="loading" class="streams-container">

      <!-- Потоки с офферами (редактируемые) -->
      <div v-for="stream in streamsWithOffers" :key="stream.id" class="stream-block">
        <div class="stream-name">
          {{ stream.name }} (ID: {{ stream.id }})
        </div>

        <!-- Панель управления потоком -->
        <div class="stream-controls">
          <el-autocomplete
            v-model="searchQuery"
            :fetch-suggestions="querySearch"
            placeholder="Поиск оффера..."
            @select="handleOfferSelect"
            clearable
            style="width: 400px"
          >
            <template #default="{ item }">
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: 500;">{{ item.name }}</span>
                <span style="color: #909399; font-size: 0.9em;">ID: {{ item.id }}</span>
              </div>
            </template>
          </el-autocomplete>
          <el-button type="primary" @click="addOffer(stream.id)" :disabled="!selectedOffer">
            + Добавить оффер
          </el-button>
        </div>

        <!-- Таблица офферов -->
        <el-table
          :data="stream.offers"
          :class="{ 'dirty-table': isDirty }"
          :row-class-name="({row}) => row.deleted ? 'deleted-row' : ''"
          style="width: 100%"
        >
          <el-table-column label="offers" min-width="350">
            <template #default="scope">
              <div style="display: flex; flex-direction: column; gap: 4px;">
                <span style="font-weight: 600; font-size: 14px;">
                  ID: {{ scope.row.offer_id }}
                </span>
                <span
                  style="font-size: 13px; line-height: 1.4; cursor: help;"
                  :title="scope.row.offer_name"
                >
                  {{ scope.row.offer_name && scope.row.offer_name.length > 70
                      ? scope.row.offer_name.slice(0, 70) + '...'
                      : scope.row.offer_name }}
                </span>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="share" width="150" align="center">
            <template #default="scope">
              <div style="display: flex; align-items: center; justify-content: center; gap: 8px;">
                <span>{{ scope.row.share }}%</span>
                <el-tooltip
                  :content="scope.row.pinned ? 'Открепить вес' : 'Зафиксировать вес'"
                  placement="top"
                >
                  <span
                    class="pin-icon"
                    :class="{ 'pinned': scope.row.pinned }"
                    @click="togglePin(stream.id, scope.row.offer_id)"
                  >
                    📌
                  </span>
                </el-tooltip>
              </div>
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
              <el-button
                v-if="!scope.row.deleted"
                size="small"
                type="danger"
                @click="removeOffer(stream.id, scope.row.offer_id)"
              >
                Удалить
              </el-button>

              <el-button
                v-else
                size="small"
                type="success"
                @click="restoreOffer(stream.id, scope.row.offer_id)"
              >
                Вернуть
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- Потоки без офферов (только информация) -->
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
  flex: 1;
}

.dirty-banner {
  background-color: #fff3cd;
  border: 1px solid #ffc107;
  border-radius: 4px;
  padding: 12px 16px;
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.banner-actions {
  display: flex;
  gap: 10px;
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

.stream-controls {
  padding: 12px 16px;
  background-color: #fafafa;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  gap: 12px;
  align-items: center;
}

/* Обычные строки таблицы */
:deep(.el-table__body tr td) {
  background-color: #ffffff !important;
}

:deep(.el-table__body tr:hover td) {
  background-color: #f5f7fa !important;
}

/* Жёлтый фон всех ячеек при наличии изменений */
.dirty-table :deep(.el-table__body tr td) {
  background-color: #fff9e6 !important;
}

.dirty-table :deep(.el-table__body tr:hover td) {
  background-color: #fff3cd !important;
}

/* Бледный текст для удалённых офферов */
:deep(.el-table__body tr.deleted-row td) {
  background-color: #ffffff !important;
  color: #b0b0b0 !important;
}

:deep(.el-table__body tr.deleted-row:hover td) {
  background-color: #f5f5f5 !important;
}

.dirty-table :deep(.el-table__body tr.deleted-row td) {
  background-color: #fff9e6 !important;
}

.dirty-table :deep(.el-table__body tr.deleted-row:hover td) {
  background-color: #fff3cd !important;
}

:deep(.el-table__body tr.deleted-row td span),
:deep(.el-table__body tr.deleted-row td div) {
  color: #b0b0b0 !important;
}

/* Возвращаем обычный цвет кнопкам внутри удалённых строк */
:deep(.el-table__body tr.deleted-row td .el-button),
:deep(.el-table__body tr.deleted-row td .el-button span) {
  color: #fff !important;
}

:deep(.el-table__body tr.deleted-row td .el-button--success) {
  background-color: #67c23a !important;
  border-color: #67c23a !important;
}

/* Более тёмный текст активных офферов в dirty-состоянии */
.dirty-table :deep(.el-table__body tr:not(.deleted-row) td span),
.dirty-table :deep(.el-table__body tr:not(.deleted-row) td div) {
  color: #1a1a1a !important;
}

/* Иконка фиксации веса */
.pin-icon {
  cursor: pointer;
  opacity: 0.3;
  font-size: 16px;
  transition: opacity 0.2s, transform 0.2s;
  user-select: none;
}

.pin-icon:hover {
  opacity: 0.6;
  transform: scale(1.1);
}

.pin-icon.pinned {
  opacity: 1;
  color: #000;
}

:deep(.el-table__body tr.deleted-row) .pin-icon {
  display: none;
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