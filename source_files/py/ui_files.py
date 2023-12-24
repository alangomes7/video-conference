ui_server_glade = """
<?xml version="1.0" encoding="UTF-8"?>
<!-- Generated with glade 3.40.0 -->
<interface>
  <requires lib="gtk+" version="3.24"/>
  <object class="GtkTextBuffer" id="text_view_buffer"/>
  <object class="GtkWindow" id="main_window">
    <property name="can-focus">False</property>
    <property name="resizable">False</property>
    <signal name="destroy" handler="on_main_window_destroy" swapped="no"/>
    <child>
      <!-- n-columns=1 n-rows=3 -->
      <object class="GtkGrid" id="grid">
        <property name="visible">True</property>
        <property name="can-focus">False</property>
        <property name="halign">center</property>
        <property name="valign">center</property>
        <property name="baseline-row">1</property>
        <child>
          <object class="GtkButton" id="button_run_stop">
            <property name="label" translatable="yes">start</property>
            <property name="visible">True</property>
            <property name="can-focus">True</property>
            <property name="receives-default">True</property>
            <property name="margin-left">300</property>
            <property name="margin-right">300</property>
            <property name="margin-top">7</property>
            <property name="margin-bottom">7</property>
            <signal name="clicked" handler="on_button_start_server_clicked" swapped="no"/>
          </object>
          <packing>
            <property name="left-attach">0</property>
            <property name="top-attach">2</property>
          </packing>
        </child>
        <child>
          <object class="GtkViewport">
            <property name="visible">True</property>
            <property name="can-focus">False</property>
            <child>
              <object class="GtkLabel" id="label_title">
                <property name="width-request">40</property>
                <property name="visible">True</property>
                <property name="can-focus">False</property>
                <property name="halign">center</property>
                <property name="valign">center</property>
                <property name="margin-left">150</property>
                <property name="margin-right">149</property>
                <property name="label" translatable="yes">Server</property>
                <property name="justify">center</property>
              </object>
            </child>
          </object>
          <packing>
            <property name="left-attach">0</property>
            <property name="top-attach">0</property>
          </packing>
        </child>
        <child>
          <object class="GtkScrolledWindow">
            <property name="width-request">500</property>
            <property name="height-request">300</property>
            <property name="visible">True</property>
            <property name="can-focus">True</property>
            <property name="shadow-type">in</property>
            <property name="min-content-width">1</property>
            <child>
              <object class="GtkTextView" id="text_view_logs">
                <property name="width-request">0</property>
                <property name="visible">True</property>
                <property name="can-focus">True</property>
                <property name="buffer">text_view_buffer</property>
              </object>
            </child>
          </object>
          <packing>
            <property name="left-attach">0</property>
            <property name="top-attach">1</property>
          </packing>
        </child>
      </object>
    </child>
  </object>
</interface>
"""

ui_client_glade = """
<?xml version="1.0" encoding="UTF-8"?>
<!-- Generated with glade 3.40.0 -->
<interface>
  <requires lib="gtk+" version="3.24"/>
  <object class="GtkTextBuffer" id="user_log_view_text_buffer"/>
  <object class="GtkWindow" id="user_main_window">
    <property name="can-focus">False</property>
    <child>
      <!-- n-columns=1 n-rows=4 -->
      <object class="GtkGrid" id="user_main_window_grid">
        <property name="visible">True</property>
        <property name="can-focus">False</property>
        <child>
          <object class="GtkLabel">
            <property name="visible">True</property>
            <property name="can-focus">False</property>
            <property name="label" translatable="yes">Receive</property>
          </object>
          <packing>
            <property name="left-attach">0</property>
            <property name="top-attach">0</property>
          </packing>
        </child>
        <child>
          <object class="GtkScrolledWindow" id="user_monitor">
            <property name="width-request">500</property>
            <property name="height-request">300</property>
            <property name="visible">True</property>
            <property name="can-focus">True</property>
            <property name="shadow-type">in</property>
            <child>
              <object class="GtkTextView" id="user_log_view">
                <property name="width-request">500</property>
                <property name="height-request">300</property>
                <property name="visible">True</property>
                <property name="can-focus">True</property>
                <property name="buffer">user_log_view_text_buffer</property>
              </object>
            </child>
          </object>
          <packing>
            <property name="left-attach">0</property>
            <property name="top-attach">1</property>
          </packing>
        </child>
        <child>
          <object class="GtkEntry" id="user_message_input">
            <property name="visible">True</property>
            <property name="sensitive">False</property>
            <property name="can-focus">True</property>
          </object>
          <packing>
            <property name="left-attach">0</property>
            <property name="top-attach">2</property>
          </packing>
        </child>
        <child>
          <object class="GtkButton" id="user_button_send">
            <property name="label" translatable="yes">send</property>
            <property name="visible">True</property>
            <property name="sensitive">False</property>
            <property name="can-focus">True</property>
            <property name="receives-default">True</property>
            <signal name="button-press-event" handler="on_user_button_send_press" swapped="no"/>
          </object>
          <packing>
            <property name="left-attach">0</property>
            <property name="top-attach">3</property>
          </packing>
        </child>
      </object>
    </child>
  </object>
</interface>

"""

ui_test = """
<?xml version="1.0" encoding="UTF-8"?>
<!-- Generated with glade 3.40.0 -->
<interface>
  <requires lib="gtk+" version="3.24"/>
  <object class="GtkWindow" id="user_monitor">
    <property name="can-focus">False</property>
    <child>
      <placeholder/>
    </child>
  </object>
</interface>

"""