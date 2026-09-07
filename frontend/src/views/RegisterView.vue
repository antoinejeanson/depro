<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { ApiError } from '../api/client'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()

const email = ref('')
const password = ref('')
const confirm = ref('')
const error = ref('')
const submitting = ref(false)

async function onSubmit() {
  error.value = ''
  if (password.value !== confirm.value) {
    error.value = 'Passwords do not match'
    return
  }
  submitting.value = true
  try {
    await auth.register(email.value, password.value)
    router.push('/tasks')
  } catch (e) {
    error.value =
      e instanceof ApiError && e.status === 409
        ? 'This email is already registered'
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
      <p class="text-center text-sm text-gray-500">
        Create your account — passwords of 8+ characters
      </p>

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
        minlength="8"
        autocomplete="new-password"
        placeholder="Password"
        class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
      />
      <input
        v-model="confirm"
        type="password"
        required
        minlength="8"
        autocomplete="new-password"
        placeholder="Confirm password"
        class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
      />

      <p v-if="error" class="text-sm text-red-600">{{ error }}</p>

      <button
        type="submit"
        :disabled="submitting"
        class="w-full rounded-lg bg-indigo-600 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
      >
        {{ submitting ? 'Creating account…' : 'Register' }}
      </button>

      <p class="text-center text-sm text-gray-500">
        Already have an account?
        <RouterLink to="/login" class="font-medium text-indigo-600 hover:underline">
          Log in
        </RouterLink>
      </p>
    </form>
  </div>
</template>
