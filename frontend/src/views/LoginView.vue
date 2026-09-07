<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { ApiError } from '../api/client'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const email = ref('')
const password = ref('')
const error = ref('')
const submitting = ref(false)

async function onSubmit() {
  error.value = ''
  submitting.value = true
  try {
    await auth.login(email.value, password.value)
    const redirect =
      typeof route.query.redirect === 'string' ? route.query.redirect : '/tasks'
    router.push(redirect)
  } catch (e) {
    error.value =
      e instanceof ApiError && e.status === 401
        ? 'Invalid email or password'
        : 'Something went wrong. Please try again.'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="flex min-h-screen items-center justify-center bg-gray-50 p-4">
    <form
      class="w-full max-w-sm space-y-4 rounded-xl bg-white p-6 shadow"
      @submit.prevent="onSubmit"
    >
      <h1 class="text-center text-2xl font-bold text-indigo-600">depro</h1>
      <p class="text-center text-sm text-gray-500">Log in to your account</p>

      <input
        v-model="email"
        type="email"
        required
        autocomplete="email"
        placeholder="Email"
        class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
      />
      <input
        v-model="password"
        type="password"
        required
        autocomplete="current-password"
        placeholder="Password"
        class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
      />

      <p v-if="error" class="text-sm text-red-600">{{ error }}</p>

      <button
        type="submit"
        :disabled="submitting"
        class="w-full rounded-lg bg-indigo-600 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
      >
        {{ submitting ? 'Logging in…' : 'Log in' }}
      </button>

      <p class="text-center text-sm text-gray-500">
        No account?
        <RouterLink to="/register" class="font-medium text-indigo-600 hover:underline">
          Register
        </RouterLink>
      </p>
    </form>
  </div>
</template>
