<template>
  <v-dialog
    width="500"
    :value="show"
    @input="showDialog"
  >
    <v-card>
      <v-card-title>
        New bridge
      </v-card-title>

      <v-card-text class="d-flex flex-column">
        <v-form
          ref="form"
          lazy-validation
        >
          <v-select
            v-model="bridge.serial_path"
            :items="available_serial_ports"
            :label="serial_selector_label"
            :rules="[validate_required_field, is_path]"
            no-data-text="No serial ports available"
            :loading="updating_serial_ports"
            item-text="name"
            :item-value="(item) => item.by_path ? item.by_path : item.name"
            dense
          >
            <template #item="{item}">
              <v-list
                fluid
                max-width="400"
                ripple
                @mousedown.prevent
              >
                <v-list-item dense>
                  <v-list-item-content dense>
                    <v-list-item-title md-1>
                      Device: {{ item.name }}
                    </v-list-item-title>
                    <v-list-item-subtitle class="text-wrap">
                      Path: {{ item.by_path ? item.by_path : item.name }}
                    </v-list-item-subtitle>
                    <v-list-item-subtitle
                      v-if="item.by_path_created_ms_ago"
                      class="text-wrap"
                    >
                      Created: {{ create_time_ago(item.by_path_created_ms_ago) }}
                    </v-list-item-subtitle>
                    <div
                      v-if="item.udev_properties && item.udev_properties['ID_VENDOR']"
                    >
                      <v-list-item-subtitle class="text-wrap">
                        Info: {{ item.udev_properties["ID_VENDOR"] }} / {{ item.udev_properties["ID_MODEL"] }}
                      </v-list-item-subtitle>
                    </div>
                  </v-list-item-content>
                </v-list-item>
              </v-list>
            </template>
          </v-select>

          <v-select
            v-model="bridge.baud"
            :items="available_baudrates"
            label="Serial baudrate"
            :rules="[validate_required_field, is_baudrate]"
          />

          <v-text-field
            v-model="bridge.ip"
            :rules="[validate_required_field, is_ip_address]"
            :label="'IP address ' + bridge_mode"
          />

          <v-text-field
            v-model="bridge.udp_port"
            :counter="50"
            label="UDP port"
            :rules="[validate_required_field, is_socket_port]"
          />

          <v-btn
            color="primary"
            class="mr-4"
            @click="createBridge"
          >
            Create
          </v-btn>
        </v-form>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script lang="ts">
import { formatDistanceToNow } from 'date-fns'
import Vue from 'vue'

import Notifier from '@/libs/notifier'
import bridget from '@/store/bridget'
import system_information from '@/store/system-information'
import { Baudrate } from '@/types/common'
import { bridget_service } from '@/types/frontend_services'
import { SerialPortInfo } from '@/types/system-information/serial'
import { VForm } from '@/types/vuetify'
import back_axios from '@/utils/api'
import {
  isBaudrate,
  isFilepath,
  isIntegerString,
  isIpAddress,
  isNotEmpty,
  isSocketPort,
} from '@/utils/pattern_validators'

const notifier = new Notifier(bridget_service)

export default Vue.extend({
  name: 'BridgeCreationDialog',
  model: {
    prop: 'show',
    event: 'change',
  },
  props: {
    show: {
      type: Boolean,
      default: false,
    },
  },

  data() {
    return {
      bridge: {
        serial_path: '',
        baud: null as (number | null),
        ip: '0.0.0.0',
        udp_port: '15000',
      },
    }
  },
  computed: {
    form(): VForm {
      return this.$refs.form as VForm
    },
    available_baudrates(): {value: number, text: string}[] {
      return Object.entries(Baudrate).map(
        (baud) => ({ value: parseInt(baud[1], 10), text: baud[1] }),
      )
    },
    available_serial_ports(): SerialPortInfo[] {
      const system_serial_ports: SerialPortInfo[] | undefined = system_information.serial?.ports
      if (system_serial_ports === undefined || system_serial_ports.isEmpty()) {
        return bridget.available_serial_ports.map((port) => ({
          name: port,
          by_path: port,
          by_path_created_ms_ago: null,
          udev_properties: null,
        }))
      }

      return system_serial_ports
        .filter((serial_info) => bridget.available_serial_ports.includes(serial_info.name))
    },
    bridge_mode(): string {
      switch (this.bridge.ip) {
        case '127.0.0.1':
          return '(Server mode, local only)'
        case '0.0.0.0':
          return '(Server mode)'
        default:
          if (this.is_ip_address(this.bridge.ip) === true) {
            return '(Client mode)'
          }
          return ''
      }
    },
    updating_serial_ports(): boolean {
      return bridget.updating_serial_ports
    },
    serial_selector_label(): string {
      return this.updating_serial_ports ? 'Fetching available serial ports...' : 'Serial port'
    },
  },
  methods: {
    create_time_ago(ms_time: number): string {
      const time_now = new Date().valueOf()
      const creation_time = time_now - ms_time
      const creation_date = new Date(creation_time)
      return `${formatDistanceToNow(creation_time)} ago (${creation_date.toLocaleTimeString()})`
    },
    validate_required_field(input: string | number): (true | string) {
      const string_input = String(input)
      return isNotEmpty(string_input) ? true : 'Required field.'
    },
    is_ip_address(input: string): (true | string) {
      return isIpAddress(input) ? true : 'Invalid IP.'
    },
    is_path(input: string): (true | string) {
      return isFilepath(input) ? true : 'Invalid path.'
    },
    is_socket_port(input: string): (true | string) {
      if (!isIntegerString(input)) {
        return 'Please use an integer value.'
      }
      const int_input = parseInt(input, 10)
      return isSocketPort(int_input) ? true : 'Invalid port.'
    },
    is_baudrate(input: number): (true | string) {
      return isBaudrate(input) ? true : 'Invalid baudrate.'
    },
    async createBridge(): Promise<boolean> {
      // Validate form before proceeding with API request
      if (!this.form.validate()) {
        return false
      }

      bridget.setUpdatingBridges(true)
      this.showDialog(false)

      await back_axios({
        method: 'post',
        url: `${bridget.API_URL}/bridges`,
        timeout: 10000,
        data: this.bridge,
      })
        .then(() => {
          this.form.reset()
        })
        .catch((error) => {
          notifier.pushBackError('BRIDGE_CREATE_FAIL', error)
        })
      return true
    },
    showDialog(state: boolean) {
      this.$emit('change', state)
    },
  },
})
</script>

<style>
</style>
