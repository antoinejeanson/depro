import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import CalendarView from './views/CalendarView.vue'
import LoginView from './views/LoginView.vue'
import RegisterView from './views/RegisterView.vue'
import SessionView from './views/SessionView.vue'
import TasksView from './views/TasksView.vue'

export const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/tasks' },
  { path: '/tasks', name: 'tasks', component: TasksView },
  { path: '/calendar', name: 'calendar', component: CalendarView },
  { path: '/session', name: 'session', component: SessionView },
  { path: '/login', name: 'login', component: LoginView, meta: { public: true } },
  { path: '/register', name: 'register', component: RegisterView, meta: { public: true } },
  { path: '/:pathMatch(.*)*', redirect: '/tasks' },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})
