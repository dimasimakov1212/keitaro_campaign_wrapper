<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

import { useRouter } from 'vue-router'
const router = useRouter()

// Состояние
const campaigns = ref([])
const offers = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const isCreating = ref(false)

// Форма создания
const form = ref({
  name: '',
  geo_code: '',
  offer_id: null
})
const selectedOfferName = ref('') // <-- Для отображения имени в автокомплите

// Загрузка данных при старте
const fetchData = async () => {
  loading.value = true
  try {
    const [campaignsRes, offersRes] = await Promise.all([
      axios.get('/api/campaigns'),
      axios.get('/api/offers')
    ])
    campaigns.value = campaignsRes.data.campaigns
    offers.value = offersRes.data.offers
  } catch (error) {
    ElMessage.error('Ошибка при загрузке данных')
    console.error(error)
  } finally {
    loading.value = false
  }
}

// Логика автокомплита: фильтрация локально
const querySearch = (queryString, cb) => {
  const results = queryString
    ? offers.value.filter(createFilter(queryString))
    : offers.value
  cb(results)
}

const createFilter = (queryString) => {
  return (offer) => {
    return offer.name.toLowerCase().includes(queryString.toLowerCase())
  }
}

// При выборе оффера из списка сохраняем его ID в форму
const handleSelectOffer = (item) => {
  form.value.offer_id = item.id
  selectedOfferName.value = item.name
}

// Отправка формы создания
const submitForm = async () => {
  if (!form.value.name || !form.value.geo_code || !form.value.offer_id) {
    ElMessage.warning('Заполните все поля, включая выбор оффера из списка')
    return
  }

  isCreating.value = true

  try {
    const response = await axios.post('/api/campaigns/create', form.value)
    ElMessage.success(response.data.message)
    dialogVisible.value = false
    
    // Очищаем форму и обновляем список
    form.value = { name: '', geo_code: '', offer_id: null }
    selectedOfferName.value = ''
    fetchData()
  } catch (error) {
    const errorMsg = error.response?.data?.detail || 'Ошибка при создании кампании'
    ElMessage.error(errorMsg)
  } finally {
    isCreating.value = false
  }
}

onMounted(() => {
  fetchData()
})
</script>

<template>
  <div class="container">
    <h1>Keitaro Campaign Wrapper</h1>
    
    <el-button type="primary" @click="dialogVisible = true" size="large">
      + Создать кампанию
    </el-button>

    <el-table :data="campaigns" style="width: 100%; margin-top: 20px" v-loading="loading">
      <el-table-column prop="id" label="ID" width="100" />
      <el-table-column prop="name" label="Название кампании" />
      <el-table-column label="Действия" width="150">
        <template #default="scope">
          <el-button 
            size="small" 
            type="success" 
            @click="router.push(`/campaigns/${scope.row.id}`)"
          >
            Редактировать
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Модальное окно создания -->
    <el-dialog v-model="dialogVisible" title="Создание новой кампании" width="500px">
      <el-form :model="form" label-width="120px">
        <el-form-item label="Название">
          <el-input v-model="form.name" placeholder="Например: test_ivanov_campaign1" />
        </el-form-item>
        <el-form-item label="Гео-код">
          <el-input v-model="form.geo_code" placeholder="Например: RU, US, DE" />
        </el-form-item>
        <el-form-item label="Оффер">
          <!-- Компонент автокомплита из Element Plus -->
          <el-autocomplete
            v-model="selectedOfferName"
            :fetch-suggestions="querySearch"
            placeholder="Введите название оффера для поиска"
            @select="handleSelectOffer"
            clearable
            style="width: 100%"
          >
            <template #default="{ item }">
              <div class="offer-item">
                <span class="offer-name">{{ item.name }}</span>
                <span class="offer-id">ID: {{ item.id }}</span>
              </div>
            </template>
          </el-autocomplete>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false" :disabled="isCreating">Отмена</el-button>
          <el-button type="primary" @click="submitForm" :loading="isCreating">
            Создать
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.container {
  max-width: 800px;
  margin: 40px auto;
  padding: 20px;
  font-family: Arial, sans-serif;
}
h1 {
  margin-bottom: 20px;
  color: #333;
}
.offer-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.offer-name {
  font-weight: 500;
}
.offer-id {
  color: #909399;
  font-size: 0.9em;
}
</style>