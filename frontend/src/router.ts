import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import CalendarView from './views/CalendarView.vue'
import SessionView from './views/SessionView.vue'
import TasksView from './views/TasksView.vue'

export const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/tasks' },
  { path: '/tasks', name: 'tasks', component: TasksView },
  { path: '/calendar', name: 'calendar', component: CalendarView },
  { path: '/session', name: 'session', component: SessionView },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})
