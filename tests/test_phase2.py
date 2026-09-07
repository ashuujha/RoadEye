from roadeye.phase2 import associate, Tracklet
def t(cam, lid, first, emb, gt): return Tracklet('S04',cam,lid,first,first+1,emb,(gt,),1,'x')
def test_association_respects_time_camera_and_independent_ids():
    links, ids=associate([t('c1',1,0,[1,0],7),t('c2',2,3,[1,0],7),t('c2',3,3,[0,1],8)],max_gap_s=10,min_similarity=.5)
    assert len(links)==1 and links[0]['from_camera']=='c1'
    assert ids['c1:1'].startswith('roadeye_') and ids['c2:3'] != ids['c1:1']
