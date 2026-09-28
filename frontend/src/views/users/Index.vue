<template>
  <div class="page-container">
    <el-tabs v-model="tab">
      <el-tab-pane label="用户" name="users">
        <el-card shadow="never">
          <div class="flex justify-between items-center mb-4">
            <div class="flex items-center gap-3">
              <el-input v-model="userFilters.search" placeholder="搜索用户名/邮箱/昵称" clearable style="width: 260px;" @keyup.enter="loadUsers" />
              <el-button type="primary" @click="loadUsers">搜索</el-button>
            </div>
            <el-button type="primary" @click="openUserDialog()">新建用户</el-button>
          </div>

          <el-table v-loading="userLoading" :data="users" stripe>
            <el-table-column prop="id" label="#" width="60" />
            <el-table-column prop="username" label="用户名" width="140" />
            <el-table-column prop="nickname" label="昵称" width="140" />
            <el-table-column prop="email" label="邮箱" min-width="200" />
            <el-table-column label="角色" min-width="220">
              <template #default="{ row }">
                <el-tag v-for="r in row.role_codes" :key="r" size="small" effect="plain" style="margin-right: 4px;">{{ r }}</el-tag>
                <span v-if="row.is_superuser_user" style="margin-left: 8px;">
                  <el-tag size="small" type="danger">SUPERUSER</el-tag>
                </span>
              </template>
            </el-table-column>
            <el-table-column label="启用" width="80">
              <template #default="{ row }">
                <el-switch :model-value="row.is_active" :disabled="row.is_superuser_user" @change="toggleActive(row)" />
              </template>
            </el-table-column>
            <el-table-column prop="date_joined" label="加入时间" width="170" />
            <el-table-column label="操作" width="220" fixed="right">
              <template #default="{ row }">
                <el-button size="small" @click="openUserDialog(row)">编辑</el-button>
                <el-button size="small" type="primary" @click="openRolesDialog(row)">分配角色</el-button>
                <el-popconfirm v-if="!row.is_superuser_user" title="确定删除？" @confirm="delUser(row)">
                  <template #reference>
                    <el-button size="small" type="danger" plain>删除</el-button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            v-model:current-page="userFilters.page"
            v-model:page-size="userFilters.page_size"
            :total="userTotal"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="loadUsers"
            @current-change="loadUsers"
            class="mt-4 justify-center flex"
          />
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="角色" name="roles">
        <el-card shadow="never">
          <div class="flex justify-between items-center mb-4">
            <div>
              <el-button @click="loadRoles">刷新</el-button>
            </div>
            <el-button type="primary" @click="openRoleDialog()">新建角色</el-button>
          </div>

          <el-table v-loading="roleLoading" :data="roles" stripe>
            <el-table-column prop="id" label="#" width="60" />
            <el-table-column prop="name" label="名称" width="160" />
            <el-table-column prop="code" label="代码" width="160" />
            <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
            <el-table-column prop="permissions_count" label="权限数" width="100" />
            <el-table-column prop="users_count" label="用户数" width="100" />
            <el-table-column label="系统" width="80">
              <template #default="{ row }">
                <el-tag :type="row.is_system ? 'danger' : 'info'" size="small">{{ row.is_system ? '内置' : '自定义' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <el-button size="small" @click="openRoleDialog(row)">编辑</el-button>
                <el-popconfirm v-if="!row.is_system" title="确定删除？" @confirm="delRole(row)">
                  <template #reference>
                    <el-button size="small" type="danger" plain>删除</el-button>
                  </template>
                </el-popconfirm>
                <span v-else style="font-size: 12px; color: #c0c4cc;">内置</span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="权限目录" name="perms">
        <el-card shadow="never">
          <el-table v-loading="permLoading" :data="permissions" stripe>
            <el-table-column prop="code" label="权限码" width="200" />
            <el-table-column prop="name" label="名称" width="160" />
            <el-table-column prop="description" label="描述" />
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- User create/edit dialog -->
    <el-dialog v-model="userDialog" :title="userForm.id ? '编辑用户' : '新建用户'" width="600px">
      <el-form :model="userForm" label-width="100px">
        <el-form-item label="用户名" v-if="!userForm.id"><el-input v-model="userForm.username" /></el-form-item>
        <el-form-item label="用户名" v-else><el-input v-model="userForm.username" disabled /></el-form-item>
        <el-form-item label="昵称"><el-input v-model="userForm.nickname" /></el-form-item>
        <el-form-item label="邮箱"><el-input v-model="userForm.email" /></el-form-item>
        <el-form-item label="头像URL"><el-input v-model="userForm.avatar" /></el-form-item>
        <el-form-item :label="userForm.id ? '新密码' : '密码'">
          <el-input v-model="userForm.password" type="password" show-password :placeholder="userForm.id ? '留空则不修改' : '必填'" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="userForm.is_active" :disabled="userForm.is_superuser_user" />
        </el-form-item>
        <el-form-item label="员工状态">
          <el-switch v-model="userForm.is_staff" />
        </el-form-item>
        <el-form-item label="分配角色">
          <el-select v-model="userForm.role_ids" multiple filterable style="width: 100%;">
            <el-option v-for="r in roles" :key="r.id" :label="`${r.name} (${r.code})`" :value="r.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="userDialog = false">取消</el-button>
        <el-button type="primary" @click="saveUser">保存</el-button>
      </template>
    </el-dialog>

    <!-- Role create/edit dialog -->
    <el-dialog v-model="roleDialog" :title="roleForm.id ? '编辑角色' : '新建角色'" width="700px">
      <el-form :model="roleForm" label-width="100px">
        <el-form-item label="名称"><el-input v-model="roleForm.name" /></el-form-item>
        <el-form-item label="代码" v-if="!roleForm.id"><el-input v-model="roleForm.code" placeholder="如 editor / operator" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="roleForm.description" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="权限">
          <el-select v-model="roleForm.perm_codes" multiple filterable style="width: 100%;">
            <el-option v-for="p in catalog" :key="p.code" :label="`${p.code} - ${p.name}`" :value="p.code" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="roleDialog = false">取消</el-button>
        <el-button type="primary" @click="saveRole">保存</el-button>
      </template>
    </el-dialog>

    <!-- Quick assign roles dialog -->
    <el-dialog v-model="rolesDialogVisible" title="分配角色" width="500px">
      <el-form label-width="80px">
        <p>用户: <strong>{{ currentUser?.username }}</strong></p>
        <el-form-item label="角色">
          <el-select v-model="assignRoleIds" multiple filterable style="width: 100%;">
            <el-option v-for="r in roles" :key="r.id" :label="`${r.name} (${r.code})`" :value="r.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rolesDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveAssignRoles">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { userApi, roleApi, permissionApi } from '@/api/account'

const tab = ref('users')

// Users
const users = ref([])
const userTotal = ref(0)
const userLoading = ref(false)
const userFilters = reactive({ page: 1, page_size: 20, search: '' })
const userDialog = ref(false)
const userForm = reactive({
  id: null, username: '', nickname: '', email: '', avatar: '',
  password: '', is_active: true, is_staff: false, is_superuser_user: false,
  role_ids: []
})

// Roles
const roles = ref([])
const roleLoading = ref(false)
const roleDialog = ref(false)
const roleForm = reactive({ id: null, name: '', code: '', description: '', perm_codes: [] })
const catalog = ref([])

// Permissions
const permissions = ref([])
const permLoading = ref(false)

// Assign roles dialog
const rolesDialogVisible = ref(false)
const currentUser = ref(null)
const assignRoleIds = ref([])

async function loadUsers() {
  userLoading.value = true
  try {
    const { data } = await userApi.list(userFilters)
    users.value = data.results || data
    userTotal.value = data.count || users.value.length
  } finally {
    userLoading.value = false
  }
}

async function loadRoles() {
  roleLoading.value = true
  try {
    const { data } = await roleApi.list({ page_size: 100 })
    roles.value = data.results || data
  } finally {
    roleLoading.value = false
  }
}

async function loadPermissions() {
  permLoading.value = true
  try {
    const { data } = await permissionApi.list({ page_size: 100 })
    permissions.value = data.results || data
  } finally {
    permLoading.value = false
  }
}

async function loadCatalog() {
  const { data } = await roleApi.catalog()
  catalog.value = data
}

function openUserDialog(row) {
  Object.assign(userForm, {
    id: null, username: '', nickname: '', email: '', avatar: '',
    password: '', is_active: true, is_staff: false, is_superuser_user: false,
    role_ids: []
  })
  if (row) {
    Object.assign(userForm, row, { password: '', role_ids: row.roles || [] })
  }
  userDialog.value = true
}

async function saveUser() {
  try {
    if (userForm.id) {
      const payload = { ...userForm }
      if (!payload.password) delete payload.password
      await userApi.update(userForm.id, payload)
    } else {
      await userApi.create(userForm)
    }
    ElMessage.success('已保存')
    userDialog.value = false
    loadUsers()
  } catch (e) {
    ElMessage.error('保存失败')
  }
}

async function toggleActive(row) {
  await userApi.toggleActive(row.id)
  ElMessage.success('已切换')
  loadUsers()
}

async function delUser(row) {
  await userApi.delete(row.id)
  ElMessage.success('已删除')
  loadUsers()
}

function openRolesDialog(row) {
  currentUser.value = row
  assignRoleIds.value = row.roles || []
  rolesDialogVisible.value = true
}

async function saveAssignRoles() {
  await userApi.assignRoles(currentUser.value.id, assignRoleIds.value)
  ElMessage.success('已分配')
  rolesDialogVisible.value = false
  loadUsers()
}

function openRoleDialog(row) {
  Object.assign(roleForm, { id: null, name: '', code: '', description: '', perm_codes: [] })
  if (row) {
    Object.assign(roleForm, row, { perm_codes: row.permissions || [] })
  }
  roleDialog.value = true
}

async function saveRole() {
  const payload = { ...roleForm, permissions: roleForm.perm_codes }
  if (roleForm.id) {
    await roleApi.update(roleForm.id, payload)
  } else {
    await roleApi.create(payload)
  }
  ElMessage.success('已保存')
  roleDialog.value = false
  loadRoles()
}

async function delRole(row) {
  try {
    await roleApi.delete(row.id)
    ElMessage.success('已删除')
    loadRoles()
  } catch (e) {
    ElMessage.error(e.response?.data?.error || '删除失败')
  }
}

onMounted(() => {
  loadUsers()
  loadRoles()
  loadPermissions()
  loadCatalog()
})
</script>
