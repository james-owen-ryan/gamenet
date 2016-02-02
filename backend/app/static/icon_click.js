$(function(){
    var ICON_LINK = "/gamenet/icon_click";
    var GAME_CLICK_LINK = "/gamenet/gamenet_link_click";
    var game_id = $('.gameTitle').data('game');
    var network = $('.gameTitle').data('network');
    var wiki_icon = $("img[alt='Wikipedia']").click(function(){
        $.post(ICON_LINK, {game_id: game_id, icon_type: 'wikipedia', network: network})
    });
    var youtube_icon = $("img[alt='YouTube']").click(function(){
        $.post(ICON_LINK, {game_id: game_id, icon_type: 'youtube', network: network})
    });
    var google_icon = $("img[alt='Google Images']").click(function(){
        $.post(ICON_LINK, {game_id: game_id, icon_type: 'google', network: network})
    });

    $('.relatedAndUnrelatedGamesLink').click(function(e){
        var game_dest_id = $(this).data('game-id');
        $.post(GAME_CLICK_LINK, {game_dest_id: game_dest_id, game_source_id: game_id, network: network})
    })
});