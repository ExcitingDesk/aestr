import flet as ft
from ui.lib_ui import build_lib_screen
from ui.search_ui import build_search_screen
from ui.playing_ui import build_playing_screen

def build_shell(page: ft.Page):
    body = ft.Container(expand=True)
    
    def show_library(e=None):
        body.content = build_lib_screen(page)
        page.update()
    
    def show_playing(e=None):
        body.content=build_playing_screen(page)
        page.update()
        
    def show_search(e=None):
        body.content=build_search_screen(page)
        page.update()
    
    navibar = ft.NavigationBar(selected_index=0,
                               destinations=[ft.NavigationBarDestination(icon=ft.Icons.LIBRARY_BOOKS_ROUNDED, label="Library"),
                               ft.NavigationBarDestination(icon=ft.Icons.SEARCH, label="Search"),
                            ft.NavigationBarDestination(icon=ft.Icons.PLAY_CIRCLE, label="Now Playing")])
    
    def nav_changed(e):
        index = e.control.selected_index
        match index:
            case 0:
                show_library()
            case 1:
                show_search()
            case 2:
                show_playing()
        
    navibar.on_change=nav_changed
    
    show_library()
        
    return ft.Column([body, navibar], expand=True)