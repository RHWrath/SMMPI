def on_audio_confirm(app):
    if not app.current_selected_file:
        app.info_label.configure(text="No audio file selected.")
        return
    
    app.selected_audio_path = app.current_selected_file
    
    app.info_label.configure(text="Audio file armed. Waiting for Android trigger.")
    
    app.start_trigger_listener()