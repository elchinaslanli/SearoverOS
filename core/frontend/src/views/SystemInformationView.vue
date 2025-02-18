<template>
  <v-card
    height="100%"
  >
    <v-tabs
      v-model="page_selected"
      centered
      icons-and-text
      show-arrows
    >
      <v-tabs-slider />
      <v-tab
        v-for="page in pages"
        :key="page.value"
      >
        {{ page.title }}
        <v-icon>{{ page.icon }}</v-icon>
      </v-tab>
    </v-tabs>
    <v-tabs-items v-model="page_selected">
      <v-tab-item
        v-for="page in pages"
        :key="page.value"
      >
        <processes v-if="page.value === 'process'" />
        <system-condition v-else-if="page.value === 'system_condition'" />
        <network v-else-if="page.value === 'network'" />
        <kernel v-else-if="page.value === 'kernel'" />
        <about-this-system v-else-if="page.value === 'about'" />
      </v-tab-item>
    </v-tabs-items>
  </v-card>
</template>

<script lang="ts">
import Vue from 'vue'

import AboutThisSystem from '@/components/system-information/AboutThisSystem.vue'
import Kernel from '@/components/system-information/Kernel.vue'
import Network from '@/components/system-information/Network.vue'
import Processes from '@/components/system-information/Processes.vue'
import SystemCondition from '@/components/system-information/SystemCondition.vue'
import settings from '@/libs/settings'

export interface Item {
  title: string,
  icon: string,
  value: string,
  is_pirate?: boolean,
}

export default Vue.extend({
  name: 'SystemInformationView',
  components: {
    AboutThisSystem,
    Kernel,
    Network,
    Processes,
    SystemCondition,
  },
  data() {
    return {
      settings,
      items: [
        { title: 'Processes', icon: 'mdi-view-dashboard', value: 'process' },
        { title: 'System Monitor', icon: 'mdi-speedometer', value: 'system_condition' },
        { title: 'Network', icon: 'mdi-ip-network-outline', value: 'network' },
        {
          title: 'Kernel', icon: 'mdi-text-subject', value: 'kernel', is_pirate: true,
        },
        { title: 'About', icon: 'mdi-information', value: 'about' },
      ] as Item[],
      page_selected: null as string | null,
    }
  },
  computed: {
    pages(): Item[] {
      return this.items
        .filter((item: Item) => item?.is_pirate !== true || this.settings.is_pirate_mode)
    },
  },
})
</script>
