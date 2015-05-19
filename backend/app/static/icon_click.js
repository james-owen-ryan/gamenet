$(function(){

    var game_id = $('.gameTitle').data('game');
    var wiki_icon = $("img[alt='Wikipedia']").click(function(){
        $.post("/icon_click", {game_id: game_id, icon_type: 'wikipedia'})
    });
    var youtube_icon = $("img[alt='YouTube']").click(function(){
        $.post("/icon_click", {game_id: game_id, icon_type: 'youtube'})
    });
    var google_icon = $("img[alt='Google Images']").click(function(){
        $.post("/icon_click", {game_id: game_id, icon_type: 'google'})
    });
});