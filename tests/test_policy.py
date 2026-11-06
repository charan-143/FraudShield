import numpy as np
import pytest
from fraudshield.policy import select_threshold,tier_counts
from fraudshield.policy import customer_frontier

def test_customer_frontier_exposes_infeasibility_and_preserves_ties():
    f=customer_frontier([1,0,1,0],[.9,.9,.7,.1],recall_targets=(.5,1),max_fpr=.1)
    assert f['rows'][0]['alerts']==2
    assert f['rows'][1]['alerts']==3
    assert not f['rows'][1]['within_friction_cap']
    assert f['rows'][1]['legitimate_interruptions_per_10000']==5000

def test_customer_frontier_rejects_invalid_constraints():
    with pytest.raises(ValueError):customer_frontier([0,1],[.1,.9],max_fpr=-.1)
    with pytest.raises(ValueError):customer_frontier([0,1],[.1,.9],recall_targets=(1.1,))

def test_policy_respects_ties_and_calibration_recall():
    y=np.array([1,0,1,0,0]);p=np.array([.9,.9,.7,.2,.1])
    result=select_threshold(y,p,min_recall=1)
    assert result['threshold']==.7
    assert result['calibration_alerts']==3
    assert result['calibration_recall']==1

def test_tiers_partition_including_equal_boundaries():
    assert tier_counts([.1,.3,.7,.9],.3,.7)=={'low_risk':1,'step_up_candidate':1,'analyst_review_candidate':2}
    assert sum(tier_counts([.5,.5],.5,.5).values())==2

def test_invalid_policy_inputs_fail():
    with pytest.raises(ValueError):select_threshold([1,1],[.1,.2])
    with pytest.raises(ValueError):tier_counts([float('nan')],.2,.8)
